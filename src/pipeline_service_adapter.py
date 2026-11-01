"""
Adapter to refactor monolithic pipeline to use worker service.
Allows running pipeline steps as distributed tasks.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import subprocess
import httpx
from typing import Optional, Dict, List, Any

# Add paths
_SRC = Path(__file__).resolve().parent
_SERVICES = _SRC.parent / "services" / "worker_service"

for p in [str(_SERVICES)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import PROCESSED_DIR, DATA_DIR

# Configuration
WORKER_SERVICE_URL = "http://localhost:8003"  # Worker API endpoint
USE_WORKER_SERVICE = False


class PipelineAdapter:
    """
    Adapter for pipeline to use worker service.
    Replaces sequential subprocess.run() calls with async tasks.
    """
    
    def __init__(self, use_service: bool = USE_WORKER_SERVICE):
        self.use_service = use_service
        self.client = httpx.Client(timeout=600.0) if use_service else None
    
    def run_step(self, step_name: str) -> Dict[str, Any]:
        """
        Run a pipeline step - either locally or via worker service.
        
        Steps: features.py, labels.py, model.py, backtest.py, etc.
        """
        if self.use_service:
            return self._run_step_via_service(step_name)
        else:
            return self._run_step_locally(step_name)
    
    def _run_step_via_service(self, step_name: str) -> Dict[str, Any]:
        """Execute pipeline step via worker service."""
        try:
            response = self.client.post(
                f"{WORKER_SERVICE_URL}/api/v1/pipeline/run",
                json={"step": step_name}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _run_step_locally(self, step_name: str) -> Dict[str, Any]:
        """Original monolithic logic - run script via subprocess."""
        script = _SRC / step_name
        if not script.exists():
            return {"status": "error", "error": f"Script not found: {step_name}"}
        
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:1000] if result.stderr else None
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def run_full_pipeline(self, steps: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run full pipeline - can execute sequentially or in parallel via workers.
        """
        if steps is None:
            steps = [
                "features.py",
                "labels.py",
                "model.py",
                "backtest.py",
                "baseline_rules.py",
                "kfold_comparison.py",
                "robustness.py",
                "make_figures.py"
            ]
        
        results = {}
        for step in steps:
            print(f"Running {step}...")
            result = self.run_step(step)
            results[step] = result
            
            if result.get("status") != "success":
                print(f"Warning: {step} failed")
                break
        
        return {
            "status": "completed",
            "results": results,
            "steps_run": len(results)
        }
    
    def schedule_daily_pipeline(self, hour: int = 8, minute: int = 0):
        """
        Schedule pipeline to run daily at specified time.
        In production, use Celery Beat or Prefect.
        """
        import schedule
        import time
        
        def job():
            print(f"Running scheduled pipeline at {datetime.now()}")
            result = self.run_full_pipeline()
            print(f"Pipeline completed: {result['status']}")
        
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(job)
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def close(self):
        """Cleanup."""
        if self.client:
            self.client.close()


# Global adapter
_pipeline_adapter: Optional[PipelineAdapter] = None


def get_pipeline_adapter(use_service: bool = False) -> PipelineAdapter:
    """Get or create pipeline adapter."""
    global _pipeline_adapter
    if _pipeline_adapter is None:
        _pipeline_adapter = PipelineAdapter(use_service=use_service)
    return _pipeline_adapter


# Migration helper for run_full_pipeline.py
def migrate_run_full_pipeline():
    """
    BEFORE (monolithic):
        # run_full_pipeline.py
        def run_step(script_name):
            cmd = [sys.executable, str(_SRC / script_name)]
            result = subprocess.run(cmd, check=True)
    
    AFTER (using adapter):
        # run_full_pipeline.py
        adapter = get_pipeline_adapter(use_service=True)
        result = adapter.run_step("features.py")
    """
    pass
