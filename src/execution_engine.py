"""
Institutional Order Execution & VWAP Slicing Engine
PFE 2.0 Antigravity - Capital Trust Securities Equity Desk

Provides institutional execution recommendations for large parent block orders:
- Calculates Real-time VWAP and VWAP slippage deviation
- Generates algorithmic Child Order Slicing schedule (TWAP / VWAP execution pace)
- Computes Market Impact Warning and Execution Urgency based on Signal vs Noise & Amihud liquidity
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

def calculate_vwap(trades_df):
    """
    Calculates Volume-Weighted Average Price (VWAP) for each ticker 
    from intraday execution tape prints.
    """
    if trades_df.empty:
        return {}
        
    trades_df['price'] = pd.to_numeric(trades_df['price'], errors='coerce')
    trades_df['size'] = pd.to_numeric(trades_df['size'], errors='coerce')
    trades_df['value'] = trades_df['price'] * trades_df['size']
    
    vwap_map = {}
    for ticker, grp in trades_df.groupby('ticker'):
        total_vol = grp['size'].sum()
        total_val = grp['value'].sum()
        if total_vol > 0:
            vwap_map[ticker] = float(total_val / total_vol)
        else:
            vwap_map[ticker] = float(grp['price'].mean())
            
    return vwap_map

def generate_parent_block_execution_plan(ticker, side, parent_quantity, current_price, vwap, signal_status, rvol, ofi_pct, max_slice_size=None):
    """
    Generates an institutional Parent-Child order execution schedule 
    for Capital Trust Securities block trading desk.
    Slices large parent orders into realistic micro-child orders (1,000 - 2,500 shares max per slice)
    to prevent order book sweeps and market impact.
    """
    parent_value_mad = (parent_quantity * current_price) / 1e6
    
    # Calculate realistic child order slice size for BVC liquidity
    # BVC order books typically depth 500 - 2,500 shares per limit level
    if max_slice_size is None or max_slice_size <= 0:
        # Default dynamic rule: target ~2,000 shares per child slice (or max 2.5% to 5% of parent)
        target_slice_qty = max(500, min(2500, int(np.ceil(parent_quantity / 25))))
    else:
        target_slice_qty = int(max_slice_size)
        
    slice_count = int(np.ceil(parent_quantity / target_slice_qty))
    child_slice_qty = int(np.ceil(parent_quantity / slice_count))
    child_slice_value_mad = (child_slice_qty * current_price)
    
    # Session execution duration (6 hours = 360 mins, slice release interval)
    release_interval_mins = max(2, int(360 / max(1, slice_count)))
    
    # Execution Strategy Pacing Logic based on Signal vs Noise
    if signal_status == "SIGNAL_CONFIRMED":
        urgency = "HIGH (Institutional Accumulation Active)"
        pacing_recommendation = f"Algorithmic VWAP Slice: Release 1 child order of {child_slice_qty:,} shares every {release_interval_mins} min to capture liquidity without market impact."
        slippage_risk = "LOW (Micro-Sliced Execution)"
    elif signal_status == "NOISE_UNCONFIRMED":
        urgency = "LOW (Thin Illiquid Spike - Passive Slicing)"
        pacing_recommendation = f"Passive Limit Slice: Post limit child orders at Bid in {child_slice_qty:,} share tranches across {slice_count} slices."
        slippage_risk = "MODERATE (Limit-Only Execution)"
    else:
        urgency = "NORMAL (Standard Institutional TWAP)"
        pacing_recommendation = f"Standard TWAP Pacing: Distribute {slice_count} child orders of {child_slice_qty:,} shares every {release_interval_mins} min."
        slippage_risk = "LOW"

    # Calculate VWAP Benchmark Premium / Discount
    vwap_diff_pct = 0.0
    if vwap > 0:
        vwap_diff_pct = ((current_price - vwap) / vwap) * 100.0
        
    return {
        "ticker": ticker,
        "side": side.upper(),
        "parent_quantity": parent_quantity,
        "parent_value_mad": round(parent_value_mad, 3),
        "current_price": current_price,
        "vwap": round(vwap, 2),
        "vwap_deviation_pct": round(vwap_diff_pct, 2),
        "signal_status": signal_status,
        "urgency": urgency,
        "recommended_slices": slice_count,
        "child_slice_qty": child_slice_qty,
        "child_slice_value_mad": round(child_slice_value_mad, 2),
        "release_interval_mins": release_interval_mins,
        "pacing_recommendation": pacing_recommendation,
        "slippage_risk": slippage_risk
    }

if __name__ == "__main__":
    # Quick execution test demo
    demo_plan = generate_parent_block_execution_plan(
        ticker="ATW",
        side="ACHAT",
        parent_quantity=50000,
        current_price=680.0,
        vwap=678.50,
        signal_status="SIGNAL_CONFIRMED",
        rvol=2.1,
        ofi_pct=64.2
    )
    print("="*70)
    print("CAPITAL TRUST SECURITIES - INSTITUTIONAL PARENT BLOCK EXECUTION PLAN")
    print("="*70)
    for k, v in demo_plan.items():
        print(f"{k:<25}: {v}")
    print("="*70)
