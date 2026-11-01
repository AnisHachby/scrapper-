#!/usr/bin/env python3
"""PFE 2.0 Antigravity - End-to-End Pipeline Execution Script

Executes feature engineering, labeling, walk-forward ML cross-validation,
and out-of-sample backtesting sequentially.
"""

import sys
import subprocess
from pathlib import Path

_SRC = Path(__file__).resolve().parent

def run_step(script_name):
    script_path = _SRC / script_name
    print(f"\n==========================================")
    print(f" Executing Step: {script_name}")
    print(f"==========================================")
    cmd = [sys.executable, str(script_path)]
    result = subprocess.run(cmd, check=True)
    if result.returncode != 0:
        raise RuntimeError(f"Step {script_name} failed with exit code {result.returncode}")

def main():
    # MIGRATED: Use adapter instead of direct subprocess calls
    from adapters.pipeline_adapter import get_pipeline_adapter
    
    steps = [
        "features.py",
        "labels.py",
        "model.py",
        "backtest.py"
    ]
    
    # Use adapter - flip use_service=True to use worker service
    adapter = get_pipeline_adapter(use_service=False)
    
    for s in steps:
        result = adapter.run_step(s)
        if result.get("status") != "success":
            print(f"Step {s} failed: {result.get('error')}")
            break
        
    print("\n==========================================")
    print(" PFE 2.0 Antigravity Pipeline Completed Successfully!")
    print("==========================================")

if __name__ == "__main__":
    main()
