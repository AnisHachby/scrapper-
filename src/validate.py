import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from config import PROCESSED_DIR, RAW_DIR, RETURN_ARTIFACT_CAP

def validate_prices(df, strict=False):
    errors = []
    warnings = []
    if df.empty:
        return ["EMPTY"], []
    required = ['date','isin','close']
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Missing cols: {missing}")
        return errors, warnings
    bad = df[~df['isin'].str.match(r'^MA[0-9A-Z]{10}$', na=False)]
    if len(bad) > 0:
        errors.append(f"Bad ISIN: {len(bad)} rows")
    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
    bad_dates = df[df['date_parsed'].isna()]
    if len(bad_dates) > 0:
        errors.append(f"Bad dates: {len(bad_dates)}")
    weekends = df[df['date_parsed'].dt.weekday >= 5]
    if len(weekends) > 0:
        if strict:
            errors.append(f"Weekends: {len(weekends)}")
        else:
            warnings.append(f"Weekends: {len(weekends)}")
    price_cols = ['open','high','low','close']
    if all(c in df.columns for c in price_cols):
        for c in price_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        for c in price_cols:
            zeros = df[df[c] == 0]
            if len(zeros) > 0:
                errors.append(f"{c} has {len(zeros)} zeros")
        bad_logic = df[(df['low']>df['high']) | (df['close']<df['low']) | (df['close']>df['high'])]
        if len(bad_logic) > 0:
            errors.append(f"Price logic: {len(bad_logic)} rows")
        for c in price_cols:
            extreme = df[df[c] > 5000]
            if len(extreme) > 0:
                warnings.append(f"{c} has {len(extreme)} >5000")
    if 'reference_price' in df.columns:
        null_ref = df['reference_price'].isna().sum()
        if null_ref == len(df):
            errors.append("reference_price 100% missing")
    dupes = df.duplicated(subset=['date','isin'], keep=False).sum()
    if dupes > 0:
        errors.append(f"Duplicates: {dupes}")
    return errors, warnings

def validate_transactions(df):
    errors = []
    warnings = []
    if df.empty:
        return ["EMPTY"], []
    for c in ['quantity','value']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            neg = df[df[c] < 0]
            if len(neg) > 0:
                errors.append(f"Negative {c}: {len(neg)}")
    return errors, warnings

def validate_features(df):
    errors = []
    warnings = []
    if df.empty:
        return ["EMPTY"], []
    req = ['date','isin','close','return_']
    missing = [c for c in req if c not in df.columns]
    if missing:
        errors.append(f"Missing cols: {missing}")
    df['return_'] = pd.to_numeric(df['return_'], errors='coerce')
    extreme = df[df['return_'].abs() > RETURN_ARTIFACT_CAP]
    if len(extreme) > 0:
        warnings.append(f"Extreme returns: {len(extreme)}")
    num_cols = df.select_dtypes(include=[np.number]).columns
    for c in num_cols:
        infs = df[np.isinf(df[c])]
        if len(infs) > 0:
            errors.append(f"{c} has Inf")
    return errors, warnings

def validate_labels(df):
    errors = []
    warnings = []
    if df.empty:
        return ["EMPTY"], []
    req = ['date','isin','return_','forward_return','label']
    missing = [c for c in req if c not in df.columns]
    if missing:
        errors.append(f"Missing cols: {missing}")
    if 'label' in df.columns:
        pos = df[df['label'] == 1]
        if len(pos) < 10:
            warnings.append(f"Few positives: {len(pos)}")
    return errors, warnings

def run_all():
    print("="*70)
    print("VALIDATION REPORT")
    print("="*70)
    all_errs = []
    all_warns = []
    files = {
        'prices': PROCESSED_DIR / 'prices_raw.parquet',
        'transactions': PROCESSED_DIR / 'transactions_raw.parquet',
        'features': PROCESSED_DIR / 'features.parquet',
        'labels': PROCESSED_DIR / 'labeled.parquet',
    }
    for name, path in files.items():
        print(f"\n[{name.upper()}] {path.name}")
        print("-"*70)
        if not path.exists():
            print("  NOT FOUND")
            all_errs.append(f"{name} not found")
            continue
        df = pd.read_parquet(path)
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {df.columns.tolist()}")
        if name == 'prices':
            e, w = validate_prices(df)
        elif name == 'transactions':
            e, w = validate_transactions(df)
        elif name == 'features':
            e, w = validate_features(df)
        elif name == 'labels':
            e, w = validate_labels(df)
        else:
            e, w = [], []
        all_errs.extend(e)
        all_warns.extend(w)
        if e:
            for err in e:
                print(f"  ERROR: {err}")
        else:
            print("  OK")
        if w:
            for warn in w:
                print(f"  WARN: {warn}")
    print("\n" + "="*70)
    print(f"TOTAL ERRORS: {len(all_errs)}, WARNINGS: {len(all_warns)}")
    print("="*70)
    if all_errs:
        print("\nERRORS:")
        for e in all_errs:
            print(f"  X {e}")
    if all_warns:
        print("\nWARNINGS:")
        for w in all_warns:
            print(f"  ! {w}")
    if not all_errs and not all_warns:
        print("\nALL CHECKS PASSED")
    return all_errs, all_warns

if __name__ == "__main__":
    run_all()
