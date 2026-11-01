"""
Adapter: Wraps run_full_pipeline.py to use Worker Service.
"""
import sys
from pathlib import Path
import subprocess
from typing import Optional

_SRC = Path(__file__).resolve().parent
_SERVICES = _SRC.parent.parent / "services" / "worker_service"

for p in [str(_SERVICES)]:
    if p not in sys.path:
        sys.path.insert(0, p)

USE_SERVICE = False  # Flip to True to use worker service


class PipelineAdapter:
    """Wraps pipeline logic - local or via service."""
    
    def __init__(self, use_service: bool = USE_SERVICE):
        self.use_service = use_service
    
    def run_step(self, script_name: str) -> dict:
        """Run one pipeline step."""
        if self.use_service:
            return self._run_via_service(script_name)
        else:
            return self._run_locally(script_name)
    
    def _run_locally(self, script_name: str) -> dict:
        """Original subprocess.run logic."""
        script = _SRC / script_name
        if not script.exists():
            return {"status": "error", "error": f"Not found: {script_name}"}
        
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=600
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500] if result.stderr else None
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _run_via_service(self, script_name: str) -> dict:
        """Call worker service."""
        import httpx
        try:
            with httpx.Client(timeout=600) as client:
                r = client.post(
                    "http://localhost:8003/api/v1/pipeline/run",
                    json={"step": script_name}
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def run_pipeline(self, steps: list) -> dict:
        """Run full pipeline."""
        results = {}
        for step in steps:
            print(f"Running {step}...")
            result = self.run_step(step)
            results[step] = result
            if result.get("status") != "success":
                break
        return {"status": "completed", "results": results}


# Singleton
_instance = None


def get_pipeline_adapter(use_service: bool = USE_SERVICE):
    """Get or create pipeline adapter."""
    global _instance
    if _instance is None:
        _instance = PipelineAdapter(use_service=use_service)
    return _instance
