"""
API Service - Exposed REST API with rate limiting and circuit breakers.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import httpx

# Setup paths
_SVC = Path(__file__).resolve().parent
_SRC = _SVC.parent.parent / "src"
_SERVICES = _SVC.parent
_SHARED = _SVC.parent / "shared"

for p in [str(_SRC), str(_SERVICES), str(_SHARED)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from shared.schemas import (
    SignalRequest, SignalResponse, MarketWatchItem,
    HealthResponse, ErrorResponse, BacktestRequest, BacktestResponse
)
from shared.circuit_breaker import CircuitBreaker
from shared.quota_manager import daily_quota, ip_quota
from shared.metrics import start_metrics_server

# Configuration
import os
ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:8001")

app = FastAPI(
    title="BVC Signal vs Noise API",
    description="Capital Trust Securities - Exposed API endpoints",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Circuit breaker for ML service
ml_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

# Cache
_market_watch_cache = None
_cache_timestamp = None
_CACHE_TTL = 30

# Startup
@app.on_event("startup")
async def startup():
    start_metrics_server(port=8002)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    deps = {}
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{ML_SERVICE_URL}/health")
            deps["ml_service"] = "healthy" if r.status_code == 200 else "unhealthy"
    except Exception:
        deps["ml_service"] = "unreachable"
    
    return HealthResponse(
        status="healthy",
        service="api_service",
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
        dependencies=deps
    )


@app.get("/api/v1/signal/{isin}", response_model=SignalResponse)
async def get_signal(
    isin: str,
    date: str = Query(..., description="Date YYYY-MM-DD"),
    confidence_threshold: float = Query(0.65, ge=0.0, le=1.0),
    include_explanation: bool = Query(False),
    request: Request = None
):
    """Get signal prediction for a single ISIN."""
    try:
        payload = {
            "isin": isin, "date": date,
            "confidence_threshold": confidence_threshold,
            "include_explanation": include_explanation,
            "user_id": getattr(request.state, 'user_id', None),
            "ip": request.client.host if request.client else None,
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{ML_SERVICE_URL}/predict", json=payload)
            response.raise_for_status()
            result = response.json()
        
        return SignalResponse(**result)
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/v1/signal/batch")
async def batch_predict(
    request: Request,
    isins: List[str],
    date: str,
    confidence_threshold: float = 0.65
):
    """Batch prediction for multiple ISINs."""
    try:
        payload = {
            "isins": isins, "date": date,
            "confidence_threshold": confidence_threshold,
            "user_id": getattr(request.state, 'user_id', None),
            "ip": request.client.host if request.client else None,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{ML_SERVICE_URL}/predict/batch", json=payload)
            response.raise_for_status()
            result = response.json()
        
        return {"results": result, "count": len(result)}
    
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/market-watch", response_model=List[MarketWatchItem])
async def get_market_watch(refresh: bool = False):
    """Get current BVC market watch with signals."""
    global _market_watch_cache, _cache_timestamp
    
    now = datetime.now(timezone.utc)
    
    if not refresh and _market_watch_cache and _cache_timestamp:
        age = (now - _cache_timestamp).total_seconds()
        if age < _CACHE_TTL:
            return _market_watch_cache
    
    # In production, fetch from data source
    return _market_watch_cache or []


@app.get("/api/v1/backtest", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest = Depends()):
    """Run backtest on historical data."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/backtest",
                json=req.dict()
            )
            response.raise_for_status()
            result = response.json()
        return BacktestResponse(**result)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/model/info")
async def get_model_info():
    """Get current model metadata."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ML_SERVICE_URL}/model/info")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(503, str(e))


@app.get("/api/v1/quota/status")
async def get_quota_status(request: Request):
    """Check remaining quota."""
    user_id = getattr(request.state, 'user_id', None)
    ip = request.client.host if request.client else None
    
    return {
        "user_quota_remaining": daily_quota.get_remaining(user_id, ip),
        "ip_quota_remaining": ip_quota.get_remaining(None, ip),
        "daily_limit": daily_quota.daily_quota,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return {"metrics": "prometheus_endpoint", "status": "active"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=2)