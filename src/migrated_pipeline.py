"""
MIGRATED run_full_pipeline.py - Now uses worker service adapter.
This replaces the monolithic pipeline runner.
"""
import sys
from pathlib import Path
from typing import Optional, List

# Add paths
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pipeline_service_adapter import get_pipeline_adapter, PipelineAdapter


def run_step(script_name: str) -> dict:
    """
    Refactored: delegates to adapter.
    Can run locally OR via worker service.
    """
    adapter = get_pipeline_adapter(use_service=False)  # Change to True to use service
    return adapter.run_step(script_name)


def main():
    """
    Refactored main() - uses adapter pattern.
    Set USE_WORKER_SERVICE in pipeline_service_adapter.py to True to use remote workers.
    """
    steps = [
        "features.py",
        "labels.py",
        "model.py",
        "backtest.py"
    ]
    
    adapter = get_pipeline_adapter(use_service=False)
    
    print("\n==========================================")
    print(" PFE 2.0 Antigravity Pipeline")
    print("==========================================\n")
    
    results = adapter.run_full_pipeline(steps)
    
    print("\n==========================================")
    print(f" Pipeline Completed: {results['status']}")
    print(f" Steps run: {results['steps_run']}/{len(steps)}")
    print("==========================================\n")
    
    # Print summary
    for step, result in results['results'].items():
        status = result.get('status', 'unknown')
        print(f"{step}: {status}")


if __name__ == "__main__":
    main()
