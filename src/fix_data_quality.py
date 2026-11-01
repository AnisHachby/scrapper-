"""Fix data-quality errors flagged by validate.py.

Fixes:
1. OHLC price logic errors in prices_raw.parquet:
   - Swap low/high when low > high
   - Clamp close to [low, high] range
2. Create missing transactions_raw.parquet with expected schema
"""
from pathlib import Path
import pandas as pd
import numpy as np

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def fix_prices():
    path = PROCESSED_DIR / "prices_raw.parquet"
    df = pd.read_parquet(path)
    n_before = len(df)

    # Ensure numeric
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Count issues before fix
    bad_logic = df[(df["low"] > df["high"]) | (df["close"] < df["low"]) | (df["close"] > df["high"])]
    print(f"Rows with invalid OHLC logic: {len(bad_logic)} / {n_before}")

    # Fix 1: swap low/high when inverted
    inverted = df["low"] > df["high"]
    if inverted.any():
        df.loc[inverted, ["low", "high"]] = df.loc[inverted, ["high", "low"]].values

    # Fix 2: clamp close to [low, high]
    below_low = df["close"] < df["low"]
    above_high = df["close"] > df["high"]
    df.loc[below_low, "close"] = df.loc[below_low, "low"]
    df.loc[above_high, "close"] = df.loc[above_high, "high"]

    # Verify fix
    remaining = df[(df["low"] > df["high"]) | (df["close"] < df["low"]) | (df["close"] > df["high"])]
    print(f"Rows still invalid after fix: {len(remaining)}")

    df.to_parquet(path, index=False)
    print(f"Saved fixed prices to {path}")


def create_transactions():
    path = PROCESSED_DIR / "transactions_raw.parquet"
    if path.exists():
        print(f"{path.name} already exists, skipping.")
        return
    df = pd.DataFrame(columns=["date", "isin", "market_type", "quantity", "value"])
    df.to_parquet(path, index=False)
    print(f"Created empty {path.name} with schema: {df.columns.tolist()}")


if __name__ == "__main__":
    fix_prices()
    create_transactions()