"""
Observability setup for API service.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Structured logging setup
def setup_logging(level: str = "info"):
    """Setup structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


class MetricsCollector:
    """Collect and expose metrics."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        if enabled:
            try:
                from shared.metrics import start_metrics_server
                start_metrics_server(port=8002)
            except Exception as e:
                logging.warning(f"Metrics disabled: {e}")
    
    def record_signal(self, signal_type: str, confidence: float):
        """Record a signal generation."""
        if self.enabled:
            try:
                from shared.metrics import signals_generated, signal_confidence
                signals_generated.labels(signal_type=signal_type).inc()
                signal_confidence.observe(confidence)
            except Exception:
                pass
    
    def record_abstention(self, reason: str):
        """Record an abstention event."""
        if self.enabled:
            try:
                from shared.metrics import abstentions
                abstentions.labels(reason=reason).inc()
            except Exception:
                pass
    
    def record_api_call(self, endpoint: str, method: str, status: int, duration: float):
        """Record API call metrics."""
        if self.enabled:
            try:
                from shared.metrics import api_latency, api_requests
                api_latency.labels(endpoint=endpoint, method=method).observe(duration)
                api_requests.labels(endpoint=endpoint, method=method, status=str(status)).inc()
            except Exception:
                pass
