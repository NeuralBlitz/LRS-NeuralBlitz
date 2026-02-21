"""
NeuralBlitz External API Integration Connectors
Provides unified interface for external AI and blockchain services
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
from functools import wraps
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Base exception for connector errors"""

    pass


class AuthenticationError(ConnectorError):
    """API authentication failed"""

    pass


class RateLimitError(ConnectorError):
    """Rate limit exceeded"""

    pass


class TimeoutError(ConnectorError):
    """Request timeout"""

    pass


class ValidationError(ConnectorError):
    """Input validation failed"""

    pass


class CircuitBreakerOpenError(ConnectorError):
    """Circuit breaker is open"""

    pass


@dataclass
class ConnectorConfig:
    """Configuration for API connectors"""

    api_key: str
    base_url: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: float = 10.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    enable_caching: bool = True
    cache_ttl: int = 3600


@dataclass
class ConnectorResponse:
    """Standardized response from connectors"""

    success: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""

    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            self.state = "OPEN"


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, rate_per_second: float = 10.0):
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.time()

    def acquire(self, tokens: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def wait_for_token(self, tokens: float = 1.0):
        while not self.acquire(tokens):
            await asyncio.sleep(0.1)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (RateLimitError, TimeoutError) as e:
                    last_exception = e
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                except AuthenticationError:
                    raise  # Don't retry auth errors
                except Exception as e:
                    last_exception = e
                    logger.error(
                        f"Attempt {attempt + 1} failed with unexpected error: {e}"
                    )
                    raise

            raise last_exception

        return wrapper

    return decorator


class BaseConnector(ABC):
    """Abstract base class for all API connectors"""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout,
        )
        self.rate_limiter = RateLimiter(config.rate_limit_per_second)
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        logger.info(f"Initialized {self.__class__.__name__}")

    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hash(key_data)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Retrieve item from cache if valid"""
        if not self.config.enable_caching:
            return None

        if key in self.cache:
            timestamp = self.cache_timestamps.get(key, 0)
            if time.time() - timestamp < self.config.cache_ttl:
                return self.cache[key]
            else:
                # Expired
                del self.cache[key]
                del self.cache_timestamps[key]
        return None

    def _set_cache(self, key: str, value: Any):
        """Store item in cache"""
        if self.config.enable_caching:
            self.cache[key] = value
            self.cache_timestamps[key] = time.time()

    def _create_response(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> ConnectorResponse:
        """Create standardized response"""
        return ConnectorResponse(
            success=success,
            data=data,
            error=error,
            latency_ms=latency_ms,
            metadata=metadata or {},
            timestamp=time.time(),
        )

    async def _execute_with_protection(self, operation, *args, **kwargs):
        """Execute operation with circuit breaker and rate limiting"""
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                "Circuit breaker is open - service unavailable"
            )

        # Wait for rate limit
        await self.rate_limiter.wait_for_token()

        try:
            start_time = time.time()
            result = await operation(*args, **kwargs)
            latency = (time.time() - start_time) * 1000
            self.circuit_breaker.record_success()
            return result, latency
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise

    @abstractmethod
    async def health_check(self) -> ConnectorResponse:
        """Check connector health status"""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources"""
        pass


class ConnectorManager:
    """Manager for all external connectors"""

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self.metrics: Dict[str, Dict] = {}

    def register_connector(self, name: str, connector: BaseConnector):
        """Register a connector"""
        self.connectors[name] = connector
        self.metrics[name] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_latency_ms": 0.0,
        }
        logger.info(f"Registered connector: {name}")

    async def execute(
        self, connector_name: str, operation, *args, **kwargs
    ) -> ConnectorResponse:
        """Execute operation on specific connector with metrics"""
        if connector_name not in self.connectors:
            return ConnectorResponse(
                success=False, error=f"Connector '{connector_name}' not found"
            )

        connector = self.connectors[connector_name]
        self.metrics[connector_name]["total_requests"] += 1

        try:
            result = await operation(connector, *args, **kwargs)
            self.metrics[connector_name]["successful_requests"] += 1

            # Update average latency
            if hasattr(result, "latency_ms"):
                current_avg = self.metrics[connector_name]["average_latency_ms"]
                total = self.metrics[connector_name]["total_requests"]
                self.metrics[connector_name]["average_latency_ms"] = (
                    current_avg * (total - 1) + result.latency_ms
                ) / total

            return result
        except Exception as e:
            self.metrics[connector_name]["failed_requests"] += 1
            return ConnectorResponse(success=False, error=str(e))

    def get_metrics(self) -> Dict:
        """Get metrics for all connectors"""
        return self.metrics.copy()

    async def health_check_all(self) -> Dict[str, ConnectorResponse]:
        """Check health of all connectors"""
        results = {}
        for name, connector in self.connectors.items():
            try:
                results[name] = await connector.health_check()
            except Exception as e:
                results[name] = ConnectorResponse(
                    success=False, error=f"Health check failed: {str(e)}"
                )
        return results

    async def close_all(self):
        """Close all connectors"""
        for name, connector in self.connectors.items():
            try:
                await connector.close()
                logger.info(f"Closed connector: {name}")
            except Exception as e:
                logger.error(f"Error closing connector {name}: {e}")


# Global connector manager instance
connector_manager = ConnectorManager()
