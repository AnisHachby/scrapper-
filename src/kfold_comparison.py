import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, TimeSeriesSplit

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    PROCESSED_DIR, FEATURE_COLS, N_ESTIMATORS, MAX_DEPTH, 
    MIN_SAMPLES_LEAF, N_SPLITS, HORIZON_DAYS, MIN_POSITIVE_PER_FOLD
)

def train_and_eval(df, cv_splits, name):
    X = df[FEATURE_COLS]
    y = df['label']
    
    all_preds = []
    
    for train_idx, test_idx in cv_splits:
        y_train = y.iloc[train_idx]
        
        if y_train.sum() < MIN_POSITIVE_PER_FOLD:
            continue
            
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_test = y.iloc[test_idx]
        
        clf = RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH,
            min_samples_leaf=MIN_SAMPLES_LEAF,
            class_weight='balanced_subsample',
            random_state=42
        )
        
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        
        fold_res = df.iloc[test_idx].copy()
        fold_res['prob'] = probs
        all_preds.append(fold_res)
        
    if not all_preds:
        return 0, 0.0
        
    oos = pd.concat(all_preds)
    flagged = oos[oos['prob'] >= 0.65]
    n_flags = len(flagged)
    
    prec = flagged['label'].mean() if n_flags > 0 else 0.0
    
    return n_flags, prec

def generate_purged_kfold(df, n_splits, purge_days):
    """
    KFold without shuffle, but dropping train indices that are too close 
    in time to the test indices to avoid label leakage.
    """
    kf = KFold(n_splits=n_splits, shuffle=False)
    splits = []
    
    for train_idx, test_idx in kf.split(df):
        # We need the dates for these indices
        test_dates = df.iloc[test_idx]['date']
        min_test = test_dates.min()
        max_test = test_dates.max()
        
        # Purge train indices within purge_days of test set
        purge_before = min_test - pd.Timedelta(days=purge_days)
        purge_after = max_test + pd.Timedelta(days=purge_days)
        
        valid_train_mask = (df['date'].iloc[train_idx] < purge_before) | (df['date'].iloc[train_idx] > purge_after)
        valid_train_idx = train_idx[valid_train_mask.values]
        
        splits.append((valid_train_idx, test_idx))
        
    return splits

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    in_path = PROCESSED_DIR / "labeled.parquet"
    if not in_path.exists():
        print(f"Labeled file {in_path} not found.")
        return
        
    df = pd.read_parquet(in_path)
    
    # Replace Inf/NaN
    for col in FEATURE_COLS:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
    notable_df = df[df['is_notable']].copy()
    notable_df = notable_df.sort_values('date').reset_index(drop=True)
    
    print("Running k-fold comparisons to measure temporal leakage...")
    
    results = []
    
    # 1. Naive Shuffled K-Fold
    kf_naive = KFold(n_splits=N_SPLITS, shuffle=True, random_state=42)
    n1, p1 = train_and_eval(notable_df, list(kf_naive.split(notable_df)), "Naive K-Fold")
    results.append({"Method": "Naive K-Fold (Shuffled)", "Precision @0.65": p1})
    
    # 2. Purged K-Fold
    purged_splits = generate_purged_kfold(notable_df, N_SPLITS, HORIZON_DAYS)
    n2, p2 = train_and_eval(notable_df, purged_splits, "Purged K-Fold")
    results.append({"Method": "Purged K-Fold (Chronological)", "Precision @0.65": p2})
    
    # 3. Walk-Forward (Our baseline)
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    n3, p3 = train_and_eval(notable_df, list(tscv.split(notable_df)), "Walk-Forward")
    results.append({"Method": "Walk-Forward (Expanding)", "Precision @0.65": p3})
    
    df_res = pd.DataFrame(results)
    print("\nComparison at Threshold 0.65:")
    print(df_res.to_string(index=False, float_format=lambda x: f"{x:.1%}"))
    
    df_res.to_csv(PROCESSED_DIR / "kfold_comparison.csv", index=False)

if __name__ == "__main__":
    main()
