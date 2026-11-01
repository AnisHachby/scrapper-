"""
Circuit breaker pattern for resilient service communication.
Prevents cascade failures when downstream services are unhealthy.
"""
import time
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    States:
    - CLOSED: Normal operation, count failures
    - OPEN: Too many failures, reject immediately
    - HALF_OPEN: Allow one test request after timeout
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[float] = None
        self.total_calls = 0
        self.total_failures = 0
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to try recovery."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Raises:
            HTTPException: If circuit is OPEN
            Exception: Original exception from the function
        """
        from fastapi import HTTPException
        
        self.total_calls += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"Service temporarily unavailable. Retry after {self.recovery_timeout}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failures = 0
        elif self.state == CircuitState.CLOSED:
            self.failures = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failures += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def get_stats(self) -> Dict[str, Any]:
        """Return circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failures": self.failures,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "failure_rate": self.total_failures / max(1, self.total_calls),
            "last_failure": datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None,
        }
