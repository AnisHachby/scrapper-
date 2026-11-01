import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, REPORT_THRESHOLDS

def summarize(group, name):
    n = len(group)
    if n == 0:
        return {'group': name, 'flags': 0, 'precision': 0.0, 'recall': 0.0, 'fwd_ret': 0.0}
        
    hit_rate = group['label'].mean()
    # directional forward return
    group = group.copy()
    group['dir_fwd_ret'] = group['forward_return'] * np.sign(group['return_'])
    
    return {
        'group': name,
        'flags': n,
        'precision': hit_rate,
        'fwd_ret': group['dir_fwd_ret'].mean()
    }

def run_backtest(oos, threshold, total_positives):
    flagged = oos[oos['prob'] >= threshold]
    unflagged = oos[oos['prob'] < threshold]
    
    s_flagged = summarize(flagged, f"Flagged (>={threshold})")
    s_unflagged = summarize(unflagged, "Unflagged")
    
    # Calculate recall
    if total_positives > 0:
        s_flagged['recall'] = flagged['label'].sum() / total_positives
    else:
        s_flagged['recall'] = 0.0
        
    s_unflagged['recall'] = 1.0 - s_flagged['recall']
    
    return s_flagged, s_unflagged

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    oos_path = PROCESSED_DIR / "oos_predictions.parquet"
    if not oos_path.exists():
        print(f"OOS predictions {oos_path} not found.")
        return
        
    oos = pd.read_parquet(oos_path)
    total_positives = oos['label'].sum()
    
    baseline = summarize(oos, "Baseline (All Notable)")
    baseline['recall'] = 1.0
    
    results = []
    
    for t in REPORT_THRESHOLDS:
        s_flagged, s_unflagged = run_backtest(oos, t, total_positives)
        results.append(s_flagged)
        
    results.append(baseline)
    
    # Print formatted table
    print("\nBacktest Summary")
    print("-" * 75)
    print(f"{'Threshold':<15} | {'Flags':<8} | {'Precision':<10} | {'Recall':<10} | {'Avg Fwd Ret':<15}")
    print("-" * 75)
    
    for r in results:
        t_str = r['group']
        flags = r['flags']
        prec = f"{r['precision']:.1%}"
        rec = f"{r['recall']:.1%}"
        ret = f"{r['fwd_ret']:.1%}"
        
        print(f"{t_str:<15} | {flags:<8} | {prec:<10} | {rec:<10} | {ret:<15}")
        
    df_results = pd.DataFrame(results)
    df_results.to_csv(PROCESSED_DIR / "backtest_summary.csv", index=False)

if __name__ == "__main__":
    main()
