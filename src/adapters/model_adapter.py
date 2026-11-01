"""
Adapter: Wraps model.py to use ML Service.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

_SRC = Path(__file__).resolve().parent
_SERVICES = _SRC.parent.parent / "services" / "ml_service"
_SHARED = _SRC.parent.parent / "services" / "shared"

for p in [str(_SERVICES), str(_SHARED)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import PROCESSED_DIR, FEATURE_COLS, N_ESTIMATORS, MAX_DEPTH, MIN_SAMPLES_LEAF, N_SPLITS, MIN_POSITIVE_PER_FOLD

# Flip this to True to use ML service
USE_SERVICE = False


class ModelAdapter:
    """Wraps model.py - local or remote."""
    
    def __init__(self, use_service: bool = USE_SERVICE):
        self.use_service = use_service
        self.local_model = None
    
    def train(self, df: pd.DataFrame) -> pd.DataFrame:
        """Train model."""
        if self.use_service:
            return self._train_via_service(df)
        return self._train_locally(df)
    
    def _train_locally(self, df: pd.DataFrame) -> pd.DataFrame:
        """Original model.py logic."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.calibration import CalibratedClassifierCV
        
        df = df.copy()
        weak = (df['is_notable']) & (df['label'] == 0) & (df['volume'] > 0) & (df['volume'] < df['rvol_20d'].median())
        df.loc[weak, 'label'] = 2
        
        notable_df = df[df['is_notable']].copy().sort_values('date').reset_index(drop=True)
        if len(notable_df) == 0:
            return pd.DataFrame()
        
        X = notable_df[FEATURE_COLS]
        y = notable_df['label']
        tscv = TimeSeriesSplit(n_splits=N_SPLITS)
        oos_preds = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(notable_df)):
            y_train = y.iloc[train_idx]
            if len(y_train.unique()) < 2:
                continue
            
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            clf = RandomForestClassifier(
                n_estimators=N_ESTIMATORS, max_depth=MAX_DEPTH,
                min_samples_leaf=MIN_SAMPLES_LEAF,
                class_weight='balanced_subsample', random_state=42
            )
            clf.fit(X_train, y_train)
            probs = clf.predict_proba(X_test)[:, 1]
            
            fold_oos = notable_df.iloc[test_idx].copy()
            fold_oos['prob'] = probs
            fold_oos['fold'] = fold
            oos_preds.append(fold_oos)
        
        return pd.concat(oos_preds, ignore_index=True) if oos_preds else pd.DataFrame()
    
    def _train_via_service(self, df: pd.DataFrame) -> pd.DataFrame:
        """Call ML service."""
        import httpx
        temp_path = PROCESSED_DIR / "temp_training.parquet"
        df.to_parquet(temp_path)
        try:
            with httpx.Client(timeout=600) as client:
                resp = client.post("http://localhost:8001/train", json={"data_path": str(temp_path)})
                resp.raise_for_status()
                result = resp.json()
                return pd.read_parquet(result['oos_path'])
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def predict(self, isin: str, date: str, threshold: float = 0.65) -> dict:
        """Predict signal."""
        if self.use_service:
            return self._predict_via_service(isin, date, threshold)
        return self._predict_locally(isin, date, threshold)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_type": "RandomForestClassifier",
            "status": "ready",
            "local_mode": not self.use_service
        }

    def _predict_locally(self, isin: str, date: str, threshold: float) -> dict:
        """Local prediction."""
        if self.local_model is None:
            import joblib
            model_path = PROCESSED_DIR / "model.joblib"
            if model_path.exists():
                self.local_model = joblib.load(model_path)
            else:
                return {"signal": "ERROR", "error": "No model"}
        
        features = pd.read_parquet(PROCESSED_DIR / "features.parquet")
        features['date'] = pd.to_datetime(features['date'])
        target_date = pd.to_datetime(date)
        
        row = features[(features['isin'] == isin) & (features['date'] == target_date)]
        if row.empty:
            return {"signal": "ERROR", "error": "No data"}
        
        # Use ONLY the features the model was trained on
        model_features = self.local_model.feature_names_in_ if hasattr(self.local_model, 'feature_names_in_') else FEATURE_COLS
        X = row[model_features].fillna(0.0).replace([np.inf, -np.inf], 0.0)
        probs = self.local_model.predict_proba(X)[0]
        confidence = float(np.max(probs))
        
        if confidence < threshold:
            signal = "ABSTAIN"
        elif np.argmax(probs) == 1:
            signal = "ACHAT"
        else:
            signal = "VENTE"
        
        return {"isin": isin, "date": date, "signal": signal, "confidence": confidence, "probability": float(probs[1])}
    
    def _predict_via_service(self, isin: str, date: str, threshold: float) -> dict:
        """Call ML service."""
        import httpx
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(
                    "http://localhost:8001/predict",
                    json={"isin": isin, "date": date, "confidence_threshold": threshold}
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            return {"signal": "ERROR", "error": str(e)}


# Singleton
_instance: Optional[ModelAdapter] = None


def get_model_adapter(use_service: bool = USE_SERVICE) -> ModelAdapter:
    """Get or create model adapter."""
    global _instance
    if _instance is None:
        _instance = ModelAdapter(use_service=use_service)
    return _instance
