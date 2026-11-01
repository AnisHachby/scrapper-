import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import (
    PROCESSED_DIR, MOVE_THRESHOLD, CONFIRM_THRESHOLD, HORIZON_DAYS
)

def build_labels(features_df, move_thresh, confirm_thresh, horizon):
    df = features_df.copy()
    df['return_'] = pd.to_numeric(df['return_'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    # Sort chronologically per ISIN
    df = df.sort_values(['isin', 'date']).reset_index(drop=True)
    
    # Identify notable moves
    df['is_notable'] = df['return_'].abs() >= move_thresh
    df['forward_return'] = np.nan
    df['is_tail'] = False
    
    # Compute forward returns
    # We want cumulative return over the next `horizon` days
    def compute_forward(g):
        # Shift prices backwards: future close / current close - 1
        future_close = g['close'].shift(-horizon)
        g['forward_return'] = future_close / g['close'] - 1
        if len(g) >= horizon:
            g.iloc[-horizon:, g.columns.get_loc('is_tail')] = True
        return g
        
    df = df.groupby('isin', group_keys=False).apply(compute_forward)
    # groupby.apply may drop the group key; restore if missing
    if 'isin' not in df.columns and 'isin' in features_df.columns:
        df['isin'] = features_df.loc[df.index, 'isin'] if df.index.isin(features_df.index).all() else features_df['isin']
    
    # Drop tail obs (no forward return available)
    df = df[~df['is_tail']].copy()
    df = df.drop(columns=['is_tail'])
    
    # Assign labels
    # Confirmed if: same sign AND magnitude >= confirm_thresh
    df['direction'] = np.sign(df['return_'])
    
    def get_label(row):
        if not row['is_notable'] or pd.isna(row['forward_return']) or pd.isna(row['direction']):
            return 0
            
        forward_dir = np.sign(row['forward_return'])
        if forward_dir == row['direction'] and abs(row['forward_return']) >= confirm_thresh:
            return 1
        return 0
        
    df['label'] = df.apply(get_label, axis=1)
    
    return df

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    
    in_path = PROCESSED_DIR / "features.parquet"
    out_path = PROCESSED_DIR / "labeled.parquet"
    
    if not in_path.exists():
        print(f"Features file {in_path} not found.")
        return
        
    print(f"Loading features from {in_path}")
    features = pd.read_parquet(in_path)
    
    print(f"Labeling notable moves (threshold: {MOVE_THRESHOLD}, confirm: {CONFIRM_THRESHOLD}, horizon: {HORIZON_DAYS}d)...")
    labeled = build_labels(features, MOVE_THRESHOLD, CONFIRM_THRESHOLD, HORIZON_DAYS)
    
    labeled.to_parquet(out_path)
    
    notables = labeled[labeled['is_notable']]
    confirmed = notables[notables['label'] == 1]
    
    print(f"Saved {len(labeled)} labeled rows to {out_path}")
    print(f"Total notable moves: {len(notables)}")
    if len(notables) > 0:
        base_rate = len(confirmed) / len(notables)
        print(f"Confirmed: {len(confirmed)} (Base rate: {base_rate:.1%})")

if __name__ == "__main__":
    main()
