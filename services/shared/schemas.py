"""
Pydantic schemas for API contracts between services.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SignalRequest(BaseModel):
    """Request model for signal generation."""
    isin: str = Field(..., description="ISIN code (e.g., MA0000011489)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence for signal")
    include_explanation: bool = Field(False, description="Include SHAP-style explanation")


class SignalResponse(BaseModel):
    """Response model for signal generation."""
    isin: str
    designation: str
    date: str
    signal: str = Field(..., description="One of: ACHAT, VENTE, BRUIT, ABSTAIN")
    confidence: float = Field(..., ge=0.0, le=1.0)
    probability: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    features: Dict[str, Any] = Field(default_factory=dict)
    explanation: Optional[Dict[str, Any]] = None
    quota_remaining: Optional[int] = None


class MarketWatchItem(BaseModel):
    """Real-time market watch item."""
    ticker: str
    designation: str
    isin: str
    last_price: Optional[float] = None
    var_veille: Optional[float] = None
    volume: Optional[int] = None
    rvol: Optional[float] = None
    signal: Optional[str] = None
    confidence: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    timestamp: datetime
    version: str = "2.0.0"
    dependencies: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    timestamp: datetime


class BacktestRequest(BaseModel):
    """Request for running backtest."""
    start_date: str
    end_date: str
    threshold: float = Field(0.65, ge=0.0, le=1.0)


class BacktestResponse(BaseModel):
    """Backtest results."""
    threshold: float
    flags: int
    precision: float
    recall: float
    avg_forward_return: float
    sharpe_ratio: Optional[float] = None
