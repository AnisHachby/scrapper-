import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    PROCESSED_DIR, FEATURE_COLS, N_ESTIMATORS, MAX_DEPTH, 
    MIN_SAMPLES_LEAF, N_SPLITS, MIN_POSITIVE_PER_FOLD, 
    ROBUSTNESS_LABEL_DEFS, HORIZON_DAYS
)
from labels import build_labels

def eval_oos(df):
    tscv = TimeSeriesSplit(n_splits=N_SPLITS)
    oos_preds = []
    
    notable_df = df[df['is_notable']].copy()
    notable_df = notable_df.sort_values('date').reset_index(drop=True)
    
    X = notable_df[FEATURE_COLS]
    y = notable_df['label']
    
    for train_idx, test_idx in tscv.split(notable_df):
        y_train = y.iloc[train_idx]
        if y_train.sum() < MIN_POSITIVE_PER_FOLD:
            continue
            
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_test = y.iloc[test_idx]
        
        clf = RandomForestClassifier(
            n_estimators=N_ESTIMATORS, max_depth=MAX_DEPTH,
            min_samples_leaf=MIN_SAMPLES_LEAF, class_weight='balanced_subsample',
            random_state=42
        )
        clf.fit(X_train, y_train)
        probs = clf.predict_proba(X_test)[:, 1]
        
        fold_oos = notable_df.iloc[test_idx].copy()
        fold_oos['prob'] = probs
        oos_preds.append(fold_oos)
        
    if not oos_preds:
        return pd.DataFrame()
    return pd.concat(oos_preds, ignore_index=True)

def precision_at_threshold(oos, threshold=0.65):
    if oos.empty: return 0.0, 0
    flagged = oos[oos['prob'] >= threshold]
    if len(flagged) == 0: return 0.0, 0
    return flagged['label'].mean(), len(flagged)

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    features_path = PROCESSED_DIR / "features.parquet"
    oos_path = PROCESSED_DIR / "oos_predictions.parquet"
    
    if not features_path.exists() or not oos_path.exists():
        print("Required files missing.")
        return
        
    features = pd.read_parquet(features_path)
    oos = pd.read_parquet(oos_path)
    
    # Preprocess features once
    for col in FEATURE_COLS:
        features[col] = features[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
    print("A. Label Definition Sensitivity")
    res_a = []
    for d in ROBUSTNESS_LABEL_DEFS:
        labeled = build_labels(features, d['move'], d['confirm'], d['horizon'])
        oos_alt = eval_oos(labeled)
        prec, n = precision_at_threshold(oos_alt, 0.65)
        res_a.append({
            'Move': f"{d['move']:.0%}", 'Confirm': f"{d['confirm']:.0%}",
            'Precision': prec, 'Flags': n
        })
    df_a = pd.DataFrame(res_a)
    print(df_a.to_string(index=False, float_format=lambda x: f"{x:.1%}"))
    
    print("\nB. Stability by Calendar Year")
    res_b = []
    oos['year'] = pd.to_datetime(oos['date']).dt.year
    for y in sorted(oos['year'].unique()):
        oos_y = oos[oos['year'] == y]
        base_rate = oos_y['label'].mean()
        prec, n = precision_at_threshold(oos_y, 0.65)
        lift = prec / base_rate if base_rate > 0 else 0
        res_b.append({'Year': y, 'Base Rate': base_rate, 'Precision': prec, 'Flags': n, 'Lift': f"{lift:.1f}x"})
    df_b = pd.DataFrame(res_b)
    print(df_b.to_string(index=False, float_format=lambda x: f"{x:.1%}"))
    
    print("\nC. Stability by Liquidity Tier")
    res_c = []
    median_val = oos['value_mad'].median()
    
    for tier, mask in [('Liquid', oos['value_mad'] >= median_val), ('Illiquid', oos['value_mad'] < median_val)]:
        oos_tier = oos[mask]
        base_rate = oos_tier['label'].mean()
        prec, n = precision_at_threshold(oos_tier, 0.65)
        lift = prec / base_rate if base_rate > 0 else 0
        res_c.append({'Tier': tier, 'Base Rate': base_rate, 'Precision': prec, 'Flags': n, 'Lift': f"{lift:.1f}x"})
    df_c = pd.DataFrame(res_c)
    print(df_c.to_string(index=False, float_format=lambda x: f"{x:.1%}"))
    
    # Save combined
    with open(PROCESSED_DIR / "robustness_results.csv", 'w') as f:
        f.write("--- Label Sensitivity ---\n")
        df_a.to_csv(f, index=False)
        f.write("\n--- By Year ---\n")
        df_b.to_csv(f, index=False)
        f.write("\n--- By Tier ---\n")
        df_c.to_csv(f, index=False)

if __name__ == "__main__":
    main()
