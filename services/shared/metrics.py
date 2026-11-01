"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Try to import prometheus client, fail gracefully if not installed
try:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Signal metrics
    signals_generated = Counter(
        'bvc_signals_total',
        'Total signals generated',
        ['signal_type']
    )
    
    signal_confidence = Histogram(
        'bvc_signal_confidence',
        'Model confidence distribution',
        buckets=[0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0]
    )
    
    abstentions = Counter(
        'bvc_abstentions_total',
        'Times model refused to signal',
        ['reason']
    )
    
    # API metrics
    api_latency = Histogram(
        'bvc_api_latency_seconds',
        'API response time',
        ['endpoint', 'method']
    )
    
    api_requests = Counter(
        'bvc_api_requests_total',
        'Total API requests',
        ['endpoint', 'method', 'status']
    )
    
    # Quota metrics
    quota_rejections = Counter(
        'bvc_quota_rejections_total',
        'Quota exhaustion events',
        ['user_id']
    )
    
    quota_remaining = Gauge(
        'bvc_quota_remaining',
        'Remaining quota for user',
        ['user_id']
    )
    
    # Circuit breaker metrics
    circuit_state = Gauge(
        'bvc_circuit_breaker_state',
        'Circuit breaker state (0=closed, 1=open, 0.5=half_open)',
        ['service']
    )
    
    PROMETHEUS_ENABLED = True
    
except ImportError:
    logger.warning("prometheus_client not installed, metrics disabled")
    PROMETHEUS_ENABLED = False
    
    # Create dummy metrics
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
    
    signals_generated = DummyMetric()
    signal_confidence = DummyMetric()
    abstentions = DummyMetric()
    api_latency = DummyMetric()
    api_requests = DummyMetric()
    quota_rejections = DummyMetric()
    quota_remaining = DummyMetric()
    circuit_state = DummyMetric()


def start_metrics_server(port: int = 8002):
    """Start Prometheus metrics endpoint."""
    if PROMETHEUS_ENABLED:
        try:
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
