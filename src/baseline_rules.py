import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, FEATURE_COLS

def test_rule(oos, rvol_t, amihud_t, mom_t):
    """
    Apply a simple rule to the OOS set:
    Flag if RVOL > rvol_t AND Amihud < amihud_t AND |momentum_5d| > mom_t
    """
    flagged = oos[
        (oos['rvol_20d'] > rvol_t) &
        (oos['amihud'] < amihud_t) &
        (oos['momentum_5d'].abs() > mom_t)
    ]
    
    n_flagged = len(flagged)
    if n_flagged == 0:
        return 0, 0.0, 0.0
        
    precision = flagged['label'].mean()
    recall = flagged['label'].sum() / max(1, oos['label'].sum())
    
    return n_flagged, precision, recall

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    # We use OOS set so we evaluate on the exact same universe as the model
    oos_path = PROCESSED_DIR / "oos_predictions.parquet"
    if not oos_path.exists():
        print(f"OOS predictions {oos_path} not found.")
        return
        
    oos = pd.read_parquet(oos_path)
    
    rvol_thresholds = [1.5, 2.0, 3.0]
    amihud_thresholds = [0.5, 1.0, 2.0]
    mom_thresholds = [0.03, 0.05, 0.08]
    
    results = []
    
    print("Evaluating baseline rules...")
    for rt in rvol_thresholds:
        for at in amihud_thresholds:
            for mt in mom_thresholds:
                n, prec, rec = test_rule(oos, rt, at, mt)
                results.append({
                    'Rule': f"RVOL>{rt}, Amihud<{at}, |Mom5|>{mt}",
                    'Flags': n,
                    'Precision': prec,
                    'Recall': rec
                })
                
    df_res = pd.DataFrame(results)
    
    # Filter rules that flag at least 10 moves
    valid = df_res[df_res['Flags'] >= 10].sort_values('Precision', ascending=False)
    
    print("\nTop 5 Baseline Rules (Simple Thresholds):")
    if valid.empty:
        print("No rule found >= 10 flags.")
    else:
        print(valid.head(5).to_string(index=False))
        
        best_prec = valid.iloc[0]['Precision']
        print(f"\nBest baseline precision: {best_prec:.1%}")
        
    df_res.to_csv(PROCESSED_DIR / "baseline_results.csv", index=False)

if __name__ == "__main__":
    main()
