"""
Market regime detection for adaptive threshold management.
Automatically raises/lowers thresholds based on market conditions.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


def detect_market_regime(
    df: pd.DataFrame,
    lookback: int = 20,
    rvol_high: float = 2.0,
    rvol_low: float = 0.5,
    amihud_percentile: float = 0.9
) -> Tuple[str, Optional[float]]:
    """
    Detect current market regime and recommend adaptive threshold.
    
    Regimes:
    - NORMAL: Standard threshold (0.65)
    - NOISY: High volatility + illiquidity = raise threshold (0.80)
    - ILLIQUID: Very low volume = abstain entirely (None)
    - TRENDING: Strong momentum = lower threshold (0.55)
    
    Args:
        df: Recent feature panel with rvol_20d, amihud, momentum_5d
        lookback: Days to look back for regime detection
        rvol_high: Threshold for high relative volume
        rvol_low: Threshold for low relative volume
        amihud_percentile: Percentile for illiquidity threshold
    
    Returns:
        (regime_name: str, recommended_threshold: Optional[float])
    """
    if df.empty or len(df) < lookback:
        return "NORMAL", 0.65
    
    recent = df.tail(lookback)
    
    # Calculate regime indicators
    avg_rvol = recent['rvol_20d'].mean()
    avg_amihud = recent['amihud'].mean()
    amihud_threshold = recent['amihud'].quantile(amihud_percentile)
    avg_momentum = recent['momentum_5d'].mean()
    
    # BVC-specific regime logic
    
    # 1. ILLIQUID: Extremely low volume across the board
    if avg_rvol < rvol_low and avg_amihud > amihud_threshold:
        return "ILLIQUID", None  # Don't trade at all
    
    # 2. NOISY: High volatility + high illiquidity = noise regime
    if avg_rvol > rvol_high and avg_amihud > amihud_threshold:
        return "NOISY", 0.85  # Raise threshold to 85%
    
    # 3. TRENDING: Strong positive/negative momentum
    if abs(avg_momentum) > 0.05 and avg_rvol > 1.2:
        regime = "TRENDING_UP" if avg_momentum > 0 else "TRENDING_DOWN"
        return regime, 0.55  # Lower threshold during trends
    
    # 4. NORMAL: Default
    return "NORMAL", 0.65


def compute_regime_features(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Add regime detection features to the panel.
    """
    df = df.copy().sort_values('date')
    
    # Rolling regime indicators
    df['rvol_ma'] = df['rvol_20d'].rolling(window, min_periods=1).mean()
    df['amihud_ma'] = df['amihud'].rolling(window, min_periods=1).mean()
    df['amihud_p90'] = df['amihud'].rolling(window, min_periods=1).quantile(0.9)
    df['momentum_ma'] = df['momentum_5d'].rolling(window, min_periods=1).mean()
    
    # Regime labels
    conditions = [
        (df['rvol_ma'] < 0.5) & (df['amihud_ma'] > df['amihud_p90']),
        (df['rvol_ma'] > 2.0) & (df['amihud_ma'] > df['amihud_p90']),
        (df['momentum_ma'].abs() > 0.05) & (df['rvol_ma'] > 1.2),
    ]
    choices = ['ILLIQUID', 'NOISY', 'TRENDING']
    df['regime'] = np.select(conditions, choices, default='NORMAL')
    
    # Adaptive threshold
    threshold_map = {'ILLIQUID': None, 'NOISY': 0.85, 'TRENDING': 0.55, 'NORMAL': 0.65}
    df['adaptive_threshold'] = df['regime'].map(threshold_map)
    
    return df


def get_regime_statistics(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Compute performance metrics by regime for monitoring.
    """
    if 'regime' not in df.columns or 'label' not in df.columns:
        return {}
    
    stats = {}
    for regime in df['regime'].unique():
        subset = df[df['regime'] == regime]
        if len(subset) == 0:
            continue
        
        stats[regime] = {
            'count': len(subset),
            'positive_rate': subset['label'].mean() if 'label' in subset.columns else 0.0,
            'avg_rvol': subset['rvol_20d'].mean(),
            'avg_amihud': subset['amihud'].mean(),
        }
    
    return stats
