"""
MIGRATED dashboard_server.py - Now uses adapters.
Replaces the monolithic 3800-line dashboard_server.py.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import numpy as np

# Setup paths
_SRC = Path(__file__).resolve().parent
_DASH = _SRC.parent / "dashboard"
_DATA = _SRC.parent / "data"

for p in [str(_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import DATA_DIR, PROCESSED_DIR
from adapters.dashboard_adapter import get_dashboard_adapter
from adapters.model_adapter import get_model_adapter

app = FastAPI(
    title="Capital Trust Securities - PFE 2.0 Antigravity BVC Desk",
    description="Real-Time BVC Signal vs Noise & Order Flow Desk Assistant",
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

# Use adapter - set use_service=True to call API service
dashboard = get_dashboard_adapter(use_service=False)
model_adapter = get_model_adapter(use_service=False)


@app.get("/")
def serve_index():
    """Serve dashboard HTML."""
    index_path = _DASH / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h2>PFE 2.0 Antigravity Dashboard</h2>")


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "dashboard",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/signal/{isin}")
async def get_signal(isin: str, date: str = Query(...), threshold: float = 0.65):
    """Get signal for ISIN - MIGRATED to use adapter."""
    result = dashboard.get_signal(isin, date, threshold)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/market-watch")
async def market_watch(refresh: bool = False):
    """Get market watch - MIGRATED to use adapter."""
    items = dashboard.get_market_watch()
    return items


@app.get("/api/backtest")
async def backtest(threshold: float = 0.65):
    """Get backtest summary."""
    result = dashboard.get_backtest_summary(threshold)
    if "error" in result:
        raise HTTPException(503, result["error"])
    return result


@app.get("/api/model/info")
async def model_info():
    """Get model information."""
    info = model_adapter.get_model_info() if hasattr(model_adapter, 'get_model_info') else {}
    return info


@app.get("/api/intraday/{ticker}")
async def get_intraday(ticker: str):
    """Get intraday data for ticker."""
    try:
        intraday_files = sorted(DATA_DIR.glob("intraday/intraday_*.csv"))
        if not intraday_files:
            raise HTTPException(404, "No intraday data")
        
        latest = intraday_files[-1]
        df = pd.read_csv(latest)
        ticker_data = df[df['ticker'] == ticker]
        return ticker_data.to_dict(orient='records')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/trades/{ticker}")
async def get_trades(ticker: str):
    """Get recent trades for ticker."""
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        trades_file = DATA_DIR / "intraday" / f"trades_{today}.csv"
        
        if not trades_file.exists():
            return []
        
        df = pd.read_csv(trades_file)
        ticker_trades = df[df['ticker'] == ticker]
        return ticker_trades.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    print("Starting migrated dashboard server...")
    print("To use API service: set use_service=True in dashboard_adapter.py")
    print("To use ML service: set use_service=True in model_adapter.py")
    uvicorn.run(app, host="0.0.0.0", port=8000)
