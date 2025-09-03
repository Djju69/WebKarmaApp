"""
Monitoring and error tracking configuration.
"""
import os
from typing import Optional, Dict, Any
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import settings

def init_sentry() -> None:
    """Initialize Sentry for error tracking."""
    if not settings.SENTRY_DSN:
        return
    
    # Configure Sentry
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"{settings.PROJECT_NAME}@{settings.VERSION}",
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR,  # Send errors as events
            ),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        # release="myapp@1.0.0",
    )


def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error",
    **kwargs,
) -> None:
    ""
    Capture an exception with additional context.
    
    Args:
        exception: The exception to capture
        context: Additional context to include
        level: Error level (error, warning, info, etc.)
        **kwargs: Additional arguments to pass to sentry_sdk.capture_exception
    """
    if not settings.SENTRY_DSN:
        return
    
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        # Add environment info
        scope.set_tag("environment", settings.ENVIRONMENT)
        scope.set_tag("service", settings.PROJECT_NAME)
        
        # Set the level
        scope.level = level
        
        # Capture the exception
        sentry_sdk.capture_exception(exception, **kwargs)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> None:
    """
    Capture a message with optional context.
    
    Args:
        message: The message to capture
        level: Message level (info, warning, error, etc.)
        context: Additional context to include
        **kwargs: Additional arguments to pass to sentry_sdk.capture_message
    """
    if not settings.SENTRY_DSN:
        return
    
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        
        # Add environment info
        scope.set_tag("environment", settings.ENVIRONMENT)
        scope.set_tag("service", settings.PROJECT_NAME)
        
        # Set the level
        scope.level = level
        
        # Capture the message
        sentry_sdk.capture_message(message, level=level, **kwargs)


class MonitoringMiddleware:
    """Middleware for monitoring and error tracking."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Add request context to Sentry
        with sentry_sdk.configure_scope() as scope:
            scope.clear_breadcrumbs()
            
            # Add request data
            if "headers" in scope:
                headers = dict(scope["headers"])
                if b"x-forwarded-for" in headers:
                    scope.set_tag("ip", headers[b"x-forwarded-for"].decode())
            
            scope.set_tag("path", scope.get("path"))
            scope.set_tag("method", scope.get("method"))
        
        # Process the request
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Capture unhandled exceptions
            capture_exception(exc)
            raise


# Initialize Sentry when module is imported
init_sentry()
