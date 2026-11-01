import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import joblib

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    PROCESSED_DIR, FEATURE_COLS, N_ESTIMATORS, MAX_DEPTH, 
    MIN_SAMPLES_LEAF, N_SPLITS, MIN_POSITIVE_PER_FOLD, 
    MIN_FLAGGED, PR_THRESHOLDS
)

def walk_forward_oos(df, n_splits):
    """
    Train via expanding window TimeSeriesSplit.
    Returns out-of-sample predictions for all test folds pooled.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oos_preds = []
    
    # We only train and predict on notable moves
    notable_df = df[df['is_notable']].copy()
    notable_df = notable_df.sort_values('date').reset_index(drop=True)
    
    X = notable_df[FEATURE_COLS]
    y = notable_df['label']
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(notable_df)):
        y_train = y.iloc[train_idx]
        
        if y_train.sum() < MIN_POSITIVE_PER_FOLD:
            print(f"Skipping fold {fold}: only {y_train.sum()} positive labels in train.")
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
        
        fold_oos = notable_df.iloc[test_idx].copy()
        fold_oos['prob'] = probs
        fold_oos['fold'] = fold
        
        oos_preds.append(fold_oos)
        
    if not oos_preds:
        return pd.DataFrame()
        
    return pd.concat(oos_preds, ignore_index=True)

def precision_recall_curve(oos):
    results = []
    y_true = oos['label'].values
    probs = oos['prob'].values
    total_positives = y_true.sum()
    
    for t in PR_THRESHOLDS:
        pred = (probs >= t).astype(int)
        n_flagged = pred.sum()
        
        if n_flagged == 0:
            precision = 0.0
            recall = 0.0
        else:
            true_positives = (y_true * pred).sum()
            precision = true_positives / n_flagged
            recall = true_positives / total_positives
            
        results.append({
            'threshold': t,
            'n_flagged': n_flagged,
            'precision': precision,
            'recall': recall
        })
        
    return pd.DataFrame(results)

def pick_threshold(curve, min_flagged):
    # Filter to thresholds that flag at least min_flagged
    valid = curve[curve['n_flagged'] >= min_flagged]
    if valid.empty:
        return None
    # Pick the one with highest precision
    best_row = valid.loc[valid['precision'].idxmax()]
    return best_row['threshold']

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    in_path = PROCESSED_DIR / "labeled.parquet"
    if not in_path.exists():
        print(f"Labeled file {in_path} not found.")
        return
        
    df = pd.read_parquet(in_path)
    
    # Replace Inf/NaN in features
    for col in FEATURE_COLS:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
    print(f"Running walk-forward CV ({N_SPLITS} splits)...")
    
    # MIGRATED: Use adapter instead of direct call
    from adapters.model_adapter import get_model_adapter
    adapter = get_model_adapter(use_service=False)  # Change to True to use ML service
    oos = adapter.train(df)
    
    if oos.empty:
        print("No out-of-sample predictions generated.")
        return
        
    out_oos = PROCESSED_DIR / "oos_predictions.parquet"
    oos.to_parquet(out_oos)
    
    pr_curve = precision_recall_curve(oos)
    out_pr = PROCESSED_DIR / "precision_recall_curve.csv"
    pr_curve.to_csv(out_pr, index=False)
    
    best_t = pick_threshold(pr_curve, MIN_FLAGGED)
    print(f"\nBest threshold (>= {MIN_FLAGGED} flags): {best_t}")
    
    if best_t is not None:
        best_stats = pr_curve[pr_curve['threshold'] == best_t].iloc[0]
        precision = best_stats['precision']
        
        print(f"Precision: {precision:.1%} | Recall: {best_stats['recall']:.1%} | Flags: {int(best_stats['n_flagged'])}")
        
        if precision < 0.70:
            print("\nNOTE: 70% precision target not met. Report this honestly as a structural finding.")
            
    # Train final model on ALL data for future use
    notable_df = df[df['is_notable']]
    X_full = notable_df[FEATURE_COLS]
    y_full = notable_df['label']
    
    if y_full.sum() >= MIN_POSITIVE_PER_FOLD:
        final_model = RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH,
            min_samples_leaf=MIN_SAMPLES_LEAF,
            class_weight='balanced_subsample',
            random_state=42
        )
        final_model.fit(X_full, y_full)
        joblib.dump(final_model, PROCESSED_DIR / "model.joblib")
        print("Final model saved to model.joblib")

if __name__ == "__main__":
    main()
