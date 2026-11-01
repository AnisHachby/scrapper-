import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, FEATURE_COLS

def explain(model, feature_row):
    # Print features
    print("\n=== Feature Values ===")
    for col in FEATURE_COLS:
        val = feature_row[col].iloc[0]
        print(f"{col:<15}: {val:.4f}")
        
    X = feature_row[FEATURE_COLS]
    
    # Global prediction
    prob = model.predict_proba(X)[0, 1]
    print(f"\nModel Probability: {prob:.1%}")
    
    # Tree votes
    votes = [tree.predict_proba(X)[0, 1] for tree in model.estimators_]
    n_trees = len(votes)
    n_positive = sum(1 for v in votes if v > 0.5)
    
    print("\n=== Tree Vote Distribution ===")
    print(f"Voted Confirmed (>0.5) : {n_positive} trees")
    print(f"Voted Noise (<=0.5)    : {n_trees - n_positive} trees")
    
    # Example tree path
    print("\n=== Example Decision Path (Tree 0) ===")
    tree = model.estimators_[0].tree_
    node_indicator = model.estimators_[0].decision_path(X)
    leaf_id = model.estimators_[0].apply(X)[0]
    
    feature_names = FEATURE_COLS
    node_index = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
    
    for node_id in node_index:
        if leaf_id == node_id:
            val = tree.value[node_id][0]
            prob_leaf = val[1] / val.sum()
            print(f"-> Reach leaf node {node_id}. Probability = {prob_leaf:.1%}")
            continue
            
        f_idx = tree.feature[node_id]
        f_name = feature_names[f_idx]
        threshold = tree.threshold[node_id]
        f_val = X[f_name].iloc[0]
        
        op = "<=" if f_val <= threshold else ">"
        print(f"Node {node_id}: {f_name} ({f_val:.4f}) {op} {threshold:.4f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, help="Ticker name (e.g. 'IB MAROC')")
    parser.add_argument("--date", type=str, help="Date YYYY-MM-DD")
    args = parser.parse_args()
    
    model_path = PROCESSED_DIR / "model.joblib"
    features_path = PROCESSED_DIR / "features.parquet"
    oos_path = PROCESSED_DIR / "oos_predictions.parquet"
    
    if not model_path.exists() or not features_path.exists():
        print("Model or features not found.")
        return
        
    model = joblib.load(model_path)
    
    if args.ticker and args.date:
        features = pd.read_parquet(features_path)
        features['date'] = pd.to_datetime(features['date'])
        target_date = pd.to_datetime(args.date)
        
        row = features[(features['designation'].str.contains(args.ticker, case=False)) & 
                      (features['date'] == target_date)]
                      
        if row.empty:
            print(f"Observation not found for {args.ticker} on {args.date}")
            return
            
        print(f"Explaining prediction for {row['designation'].iloc[0]} on {args.date}")
        
    else:
        # Find most recent high-confidence flag
        if not oos_path.exists():
            print("Need OOS predictions for auto-select.")
            return
        oos = pd.read_parquet(oos_path)
        flagged = oos[oos['prob'] >= 0.70].sort_values('date', ascending=False)
        if flagged.empty:
            print("No high confidence flags found.")
            return
            
        target = flagged.iloc[0]
        print(f"Auto-selected latest flag: {target['designation']} on {target['date'].strftime('%Y-%m-%d')}")
        
        features = pd.read_parquet(features_path)
        row = features[(features['isin'] == target['isin']) & (features['date'] == target['date'])]
        
    for col in FEATURE_COLS:
        row.loc[:, col] = row[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
    explain(model, row)

if __name__ == "__main__":
    main()
