"""
Adapter: Wraps dashboard_server.py to use API Service.
"""
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import httpx

_SRC = Path(__file__).resolve().parent
_DATA = _SRC.parent.parent / "data"
_PROCESSED = _DATA / "processed"

USE_SERVICE = False  # Flip to True to use API service
API_URL = "http://localhost:8000"


class DashboardAdapter:
    """Wraps dashboard_server.py logic."""
    
    def __init__(self, use_service: bool = USE_SERVICE):
        self.use_service = use_service
        self._cache = None
        self._cache_time = None
    
    def get_signal(self, isin: str, date: str, threshold: float = 0.65) -> dict:
        """Get signal - local or via service."""
        if self.use_service:
            return self._from_api(isin, date, threshold)
        else:
            return self._local_signal(isin, date, threshold)
    
    def _from_api(self, isin: str, date: str, threshold: float) -> dict:
        """Call API service."""
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    f"{API_URL}/api/v1/signal/{isin}",
                    params={"date": date, "confidence_threshold": threshold}
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            return {"signal": "ERROR", "error": str(e)}
    
    def _local_signal(self, isin: str, date: str, threshold: float) -> dict:
        """Get signal using model adapter."""
        try:
            from adapters.model_adapter import get_model_adapter
            model = get_model_adapter(use_service=False)
            return model.predict(isin, date, threshold)
        except Exception as e:
            return {"isin": isin, "date": date, "signal": "ERROR", "error": str(e)}
    
    def get_market_watch(self) -> List[dict]:
        """Get market watch - local or via service."""
        if self.use_service:
            return self._market_watch_from_api()
        else:
            return self._local_market_watch()
    
    def _market_watch_from_api(self) -> List[dict]:
        """Call API service."""
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(f"{API_URL}/api/v1/market-watch")
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"Market watch error: {e}")
            return []
    
    def get_backtest_summary(self, threshold: float = 0.65) -> dict:
        """Get backtest summary."""
        try:
            backtest_path = _PROCESSED / "backtest_summary.csv"
            if backtest_path.exists():
                df = pd.read_csv(backtest_path)
                # The CSV has 'group' column formatted like "Flagged (>=0.65)"
                if 'group' in df.columns:
                    row = None
                    # Match pattern like "Flagged (>=0.65)"
                    search = f">={threshold:g}"
                    mask = df['group'].str.contains(search, na=False)
                    if mask.any():
                        row = df[mask].iloc[0].to_dict()
                    else:
                        # Fallback: return total summary
                        all_rows = df[df['group'].str.contains("Baseline", na=False)]
                        if not all_rows.empty:
                            row = all_rows.iloc[0].to_dict()
                    if row is not None:
                        return row
            return {"status": "no_data", "message": "Run backtest first"}
        except Exception as e:
            return {"error": str(e)}

    def _local_market_watch(self) -> List[dict]:
        """Get market watch with latest signals."""
        try:
            # Load features and OOS predictions
            features_path = _DATA / "processed" / "features.parquet"
            oos_path = _PROCESSED / "oos_predictions.parquet"
            
            if not features_path.exists() or not oos_path.exists():
                return []
            
            features = pd.read_parquet(features_path)
            oos = pd.read_parquet(oos_path)
            
            # Get latest date
            features['date'] = pd.to_datetime(features['date'])
            oos['date'] = pd.to_datetime(oos['date'])
            
            # Use latest OOS date (not features date - they may not match)
            latest_oos_date = oos['date'].max()
            latest_oos = oos[oos['date'] == latest_oos_date].copy()
            
            if latest_oos.empty:
                # Fallback: use top 20 by probability from all OOS
                latest_oos = oos.nlargest(20, 'prob')
            
            # Build market watch items
            items = []
            for _, row in latest_oos.head(20).iterrows():
                signal = "ABSTAIN"
                if row['prob'] >= 0.75:
                    signal = "ACHAT" if row.get('return_', 0) > 0 else "VENTE"
                elif row['prob'] >= 0.65:
                    signal = "WATCH"
                
                items.append({
                    'ticker': row.get('designation', 'N/A'),
                    'designation': row.get('designation', 'N/A'),
                    'isin': row.get('isin', 'N/A'),
                    'last_price': float(row.get('close', 0)) if pd.notna(row.get('close', 0)) else None,
                    'var_veille': float(row.get('return_', 0)) if pd.notna(row.get('return_', 0)) else None,
                    'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume', 0)) else None,
                    'rvol': float(row.get('rvol_20d', 0)) if pd.notna(row.get('rvol_20d', 0)) else None,
                    'signal': signal,
                    'confidence': float(row.get('prob', 0)) if pd.notna(row.get('prob', 0)) else None
                })
            
            return items
            
        except Exception as e:
            print(f"Market watch error: {e}")
            return []


# Singleton
_instance = None


def get_dashboard_adapter(use_service: bool = USE_SERVICE):
    """Get or create dashboard adapter."""
    global _instance
    if _instance is None:
        _instance = DashboardAdapter(use_service=use_service)
    return _instance
