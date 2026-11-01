"""
MIGRATED model.py - Now uses ML service adapter.
This replaces the monolithic model.py while maintaining backward compatibility.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional

# Add paths
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Import original config
from config import (
    PROCESSED_DIR, FEATURE_COLS, N_ESTIMATORS, MAX_DEPTH,
    MIN_SAMPLES_LEAF, N_SPLITS, MIN_POSITIVE_PER_FOLD,
    MIN_FLAGGED, PR_THRESHOLDS
)

# Import adapter
from adapters.model_adapter import get_model_adapter, ModelAdapter


def walk_forward_oos(df, n_splits):
    """
    Refactored: delegates to adapter.
    Can use local training OR remote ML service based on configuration.
    """
    adapter = get_model_adapter(use_service=False)  # Change to True to use service
    return adapter.train(df)


def precision_recall_curve(oos):
    """Kept for backward compatibility."""
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
    """Kept for backward compatibility."""
    valid = curve[curve['n_flagged'] >= min_flagged]
    if valid.empty:
        return None
    best_row = valid.loc[valid['precision'].idxmax()]
    return best_row['threshold']


def main():
    """
    Refactored main() - uses adapter pattern.
    Set USE_ML_SERVICE in model_service_adapter.py to True to use remote service.
    """
    import argparse
    
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    # Load data
    in_path = PROCESSED_DIR / "labeled.parquet"
    if not in_path.exists():
        print(f"Labeled file {in_path} not found.")
        return
    
    df = pd.read_parquet(in_path)
    
    # Replace Inf/NaN in features
    for col in FEATURE_COLS:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    
    print(f"Running walk-forward CV ({N_SPLITS} splits)...")
    
    # Use adapter (can switch between local and service)
    adapter = get_model_adapter(use_service=False)
    oos = adapter.train_locally(df)
    
    if oos.empty:
        print("No out-of-sample predictions generated.")
        return
    
    # Save results
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
            print("\nNOTE: 70% precision target not met.")
    
    # Train final model
    notable_df = df[df['is_notable']]
    if len(notable_df) > 0:
        from sklearn.ensemble import RandomForestClassifier
        import joblib
        
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
