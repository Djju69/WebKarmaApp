"""
Prometheus metrics configuration.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from typing import Callable, List, Optional, Tuple
import time

from app.core.config import settings

# Disable default metrics
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

# Common labels
COMMON_LABELS = ["method", "path", "status_code"]

# HTTP Requests
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    COMMON_LABELS,
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    COMMON_LABELS,
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "path"],
)

# Database Metrics
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
)

DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "table"],
)

# Business Metrics
USERS_TOTAL = Gauge("users_total", "Total number of users")
ACTIVE_USERS = Gauge("active_users_total", "Number of active users")

# Error Metrics
ERROR_COUNT = Counter(
    "errors_total",
    "Total number of errors",
    ["type", "endpoint"],
)

# Cache Metrics
CACHE_HITS = Counter("cache_hits_total", "Total cache hits", ["cache_name"])
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", ["cache_name"])
CACHE_SIZE = Gauge("cache_size_bytes", "Size of the cache in bytes", ["cache_name"])


def get_metrics() -> bytes:
    """Generate metrics in Prometheus format."""
    return generate_latest(REGISTRY)


def get_metrics_response() -> Response:
    """Get metrics as a Starlette response."""
    return Response(
        content=get_metrics(),
        media_type=CONTENT_TYPE_LATEST,
    )


def track_request_duration(
    method: str,
    path: str,
    status_code: int,
    duration: float,
) -> None:
    """Track HTTP request duration."""
    REQUEST_LATENCY.labels(
        method=method,
        path=path,
        status_code=status_code,
    ).observe(duration)


def track_request_count(
    method: str,
    path: str,
    status_code: int,
) -> None:
    """Increment request counter."""
    REQUEST_COUNT.labels(
        method=method,
        path=path,
        status_code=status_code,
    ).inc()


def track_request_in_progress(
    method: str,
    path: str,
    in_progress: bool = True,
) -> None:
    """Track requests in progress."""
    if in_progress:
        REQUEST_IN_PROGRESS.labels(method=method, path=path).inc()
    else:
        REQUEST_IN_PROGRESS.labels(method=method, path=path).dec()


def track_error(error_type: str, endpoint: str) -> None:
    """Track errors."""
    ERROR_COUNT.labels(type=error_type, endpoint=endpoint).inc()


def track_db_query(
    operation: str,
    table: str,
    duration: float,
) -> None:
    """Track database query metrics."""
    DB_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)
    DB_QUERY_COUNT.labels(operation=operation, table=table).inc()


class PrometheusMiddleware:
    """Middleware for collecting Prometheus metrics."""

    def __init__(self, app, app_name: str = "fastapi_app"):
        self.app = app
        self.app_name = app_name

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = self.get_path(scope)
        
        # Skip metrics endpoint
        if path == "/metrics":
            return await self.app(scope, receive, send)

        start_time = time.time()
        
        # Track request in progress
        track_request_in_progress(method, path)
        
        # Response status code
        status_code = 500
        
        async def send_wrapper(message):
            nonlocal status_code
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
            
            await send(message)
        
        try:
            # Process the request
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Track error
            track_error("unhandled_exception", path)
            raise
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Track metrics
            track_request_duration(method, path, status_code, duration)
            track_request_count(method, path, status_code)
            track_request_in_progress(method, path, in_progress=False)
    
    @staticmethod
    def get_path(scope) -> str:
        """Get the request path, handling path parameters."""
        path = scope["path"]
        
        # Handle path parameters
        for route in scope["app"].routes:
            match, _ = route.matches(scope)
            if match == Match.FULL:
                return route.path
        
        return path
