"""
ML Service - Dedicated model inference and training service.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from typing import Optional, Dict, Any
from datetime import datetime

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup paths
_ML = Path(__file__).resolve().parent
_SRC = _ML.parent.parent / "src"
_SHARED = _ML.parent / "shared"

for p in [str(_SRC), str(_SHARED)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import PROCESSED_DIR, FEATURE_COLS

app = FastAPI(title="BVC ML Service", version="2.0.0")

_model = None
_model_info: Dict[str, Any] = {}


@app.on_event("startup")
async def startup():
    """Load model on startup."""
    global _model, _model_info
    try:
        model_path = PROCESSED_DIR / "model.joblib"
        if model_path.exists():
            _model = joblib.load(model_path)
            _model_info = {
                "loaded_at": datetime.now().isoformat(),
                "path": str(model_path),
                "status": "loaded"
            }
            logger.info(f"Model loaded from {model_path}")
        else:
            logger.warning("No model found at startup")
            _model_info = {"status": "no_model"}
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        _model_info = {"status": "error", "error": str(e)}


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy" if _model is not None else "degraded",
        "service": "ml_service",
        "model_loaded": _model is not None,
        "timestamp": datetime.now().isoformat()
    }


class PredictRequest(BaseModel):
    isin: str
    date: str
    confidence_threshold: float = 0.65
    include_explanation: bool = False
    user_id: Optional[str] = None
    ip: Optional[str] = None


@app.post("/predict")
async def predict(req: PredictRequest):
    """Single ISIN prediction with abstain logic."""
    try:
        if _model is None:
            raise HTTPException(503, "Model not available")
        
        features_path = PROCESSED_DIR / "features.parquet"
        if not features_path.exists():
            raise HTTPException(503, "Feature data not available")
        
        features = pd.read_parquet(features_path)
        features['date'] = pd.to_datetime(features['date'])
        target_date = pd.to_datetime(req.date)
        
        row = features[(features['isin'] == req.isin) & (features['date'] == target_date)]
        if row.empty:
            raise HTTPException(404, f"No data for {req.isin}")
        
        # Use ONLY the features the model was trained on
        model_features = _model.feature_names_in_ if hasattr(_model, 'feature_names_in_') else FEATURE_COLS
        X = row[model_features].fillna(0.0).replace([np.inf, -np.inf], 0.0)
        probs = _model.predict_proba(X)[0]
        confidence = float(np.max(probs))
        pred_class = int(np.argmax(probs))
        
        if confidence < req.confidence_threshold:
            signal = "ABSTAIN"
        elif pred_class == 1:
            signal = "ACHAT"
        else:
            signal = "VENTE"
        
        result = {
            "isin": req.isin,
            "designation": row['designation'].iloc[0] if 'designation' in row.columns else req.isin,
            "date": req.date,
            "signal": signal,
            "confidence": confidence,
            "probability": float(probs[1]),
            "uncertainty": float(np.std(probs)),
            "features": row[FEATURE_COLS].iloc[0].to_dict(),
            "regime": "NORMAL",
            "quota_remaining": None
        }
        
        if req.include_explanation:
            sorted_features = sorted(
                result["features"].items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:5]
            result["explanation"] = {
                "top_features": [{"name": k, "value": float(v)} for k, v in sorted_features]
            }
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(500, str(e))


@app.post("/predict/batch")
async def batch_predict(req: dict):
    """Batch prediction."""
    results = []
    for isin in req.get("isins", []):
        try:
            single_req = PredictRequest(
                isin=isin,
                date=req["date"],
                confidence_threshold=req.get("confidence_threshold", 0.65)
            )
            result = await predict(single_req)
            results.append(result)
        except Exception as e:
            results.append({
                "isin": isin,
                "error": str(e),
                "signal": "ERROR"
            })
    return results


@app.get("/signals/latest")
async def latest_signals(limit: int = 20):
    """Get latest signals for all ISINs."""
    try:
        features_path = PROCESSED_DIR / "features.parquet"
        if not features_path.exists():
            return []
        
        features = pd.read_parquet(features_path)
        features['date'] = pd.to_datetime(features['date'])
        latest_date = features['date'].max()
        
        latest = features[features['date'] == latest_date].copy()
        
        if _model:
            # Use ONLY the features the model was trained on
            model_features = _model.feature_names_in_ if hasattr(_model, 'feature_names_in_') else FEATURE_COLS
            latest[model_features] = latest[model_features].fillna(0.0).replace([np.inf, -np.inf], 0.0)
            probs = _model.predict_proba(latest[model_features])
            latest['prob'] = probs[:, 1]
            latest['signal'] = latest['prob'].apply(
                lambda p: "ABSTAIN" if p < 0.65 else "ACHAT" if p > 0.5 else "VENTE"
            )
        else:
            latest['prob'] = 0.0
            latest['signal'] = "ABSTAIN"
        
        result = []
        for _, row in latest.head(limit).iterrows():
            result.append({
                "isin": row['isin'],
                "designation": row.get('designation', row['isin']),
                "signal": row['signal'],
                "confidence": float(row['prob']),
                "rvol": float(row.get('rvol_20d', 0)),
            })
        return result
    
    except Exception as e:
        logger.error(f"Latest signals error: {e}")
        return []


@app.get("/model/info")
async def model_info():
    """Get model information."""
    return _model_info


@app.post("/backtest")
async def backtest(req: dict):
    """Run simple backtest."""
    try:
        oos_path = PROCESSED_DIR / "oos_predictions.parquet"
        if not oos_path.exists():
            raise HTTPException(503, "No backtest data available")
        
        oos = pd.read_parquet(oos_path)
        threshold = req.get("threshold", 0.65)
        
        flagged = oos[oos['prob'] >= threshold]
        
        return {
            "threshold": threshold,
            "flags": len(flagged),
            "precision": float(flagged['label'].mean()) if len(flagged) > 0 else 0.0,
            "recall": float(flagged['label'].sum() / max(1, oos['label'].sum())),
            "avg_forward_return": float(flagged['forward_return'].mean()) if len(flagged) > 0 else 0.0,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, log_level="info")
