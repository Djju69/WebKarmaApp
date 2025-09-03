"""
Advanced logging configuration for the application with Sentry and structured logging.

Features:
- JSON and console logging
- Request context tracking
- Sentry integration
- Performance metrics
- Rotating file handler
"""
import logging
import logging.config
import os
import sys
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

import sentry_sdk
from pythonjsonlogger import jsonlogger
from sentry_sdk.integrations.logging import LoggingIntegration

T = TypeVar('T', bound=Callable[..., Any])

# Request context storage
class RequestContext:
    _request_id: str = ""
    _user_id: Optional[str] = None
    _path: Optional[str] = None
    _method: Optional[str] = None
    
    @classmethod
    def get_request_id(cls) -> str:
        if not cls._request_id:
            cls._request_id = str(uuid.uuid4())
        return cls._request_id
    
    @classmethod
    def set_request_context(
        cls, 
        request_id: Optional[str] = None, 
        user_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> None:
        if request_id:
            cls._request_id = request_id
        if user_id:
            cls._user_id = user_id
        if path:
            cls._path = path
        if method:
            cls._method = method
    
    @classmethod
    def clear(cls) -> None:
        cls._request_id = ""
        cls._user_id = None
        cls._path = None
        cls._method = None

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMATTER = os.getenv("LOG_FORMAT", "json").lower()


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Enhanced JSON formatter with request context and performance metrics."""

    def add_fields(
        self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to the log record with request context and timing."""
        super().add_fields(log_record, record, message_dict)
        
        # Standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["timestamp"] = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        
        # Environment and deployment info
        log_record["environment"] = os.getenv("ENVIRONMENT", "development")
        log_record["service"] = os.getenv("SERVICE_NAME", "karmabot-backend")
        log_record["version"] = os.getenv("APP_VERSION", "unknown")
        
        # Request context
        if RequestContext._request_id:
            log_record["request_id"] = RequestContext._request_id
        if RequestContext._user_id:
            log_record["user_id"] = RequestContext._user_id
        if RequestContext._path:
            log_record["path"] = RequestContext._path
        if RequestContext._method:
            log_record["method"] = RequestContext._method
            
        # Performance metrics
        if hasattr(record, 'duration_ms'):
            log_record["duration_ms"] = record.duration_ms
            
        # Exception details
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        # Add thread and process info
        log_record["thread"] = record.thread
        log_record["process"] = record.processName


def setup_sentry_logging() -> None:
    """Initialize Sentry logging integration if SENTRY_DSN is set."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return
        
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[sentry_logging],
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        release=os.getenv("APP_VERSION"),
    )


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger instance with request context support.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance with request context support
    """
    logger = logging.getLogger(name or __name__)
    
    # Don't add handlers if they're already configured
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)
    
    # Create formatters
    if os.getenv("LOG_FORMAT", "json").lower() == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Rotating file handler for application logs (10MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (errors only)
    error_file_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    logger.addHandler(error_file_handler)
    
    # Configure SQLAlchemy logging if enabled
    if os.getenv("SQL_DEBUG", "false").lower() == "true":
        sql_logger = logging.getLogger("sqlalchemy.engine")
        sql_logger.setLevel(logging.INFO)
        sql_logger.addHandler(console_handler)
        sql_logger.addHandler(file_handler)
    
    # Configure Uvicorn/Access logs
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = [h for h in uvicorn_access.handlers 
                             if not isinstance(h, logging.StreamHandler)]
    
    # Disable excessive logging from other libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return logger


def configure_logging() -> None:
    """Configure logging for the application."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "app.core.logging.JsonFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
                "simple": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json",
                    "filename": LOG_DIR / "app.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf8",
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json",
                    "filename": LOG_DIR / "error.log",
                    "level": "ERROR",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf8",
                },
            },
            "loggers": {
                "": {  # root logger
                    "handlers": ["console", "file", "error_file"],
                    "level": LOG_LEVEL,
                    "propagate": False,
                },
                "app": {
                    "handlers": ["console", "file", "error_file"],
                    "level": LOG_LEVEL,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy": {
                    "handlers": ["console", "file"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }
    )


def log_execution_time(logger: logging.Logger = None):
    """Decorator to log function execution time."""
    if logger is None:
        logger = get_logger(__name__)
    
    def decorator(func: T) -> T:
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (time.perf_counter() - start_time) * 1000  # ms
                logger.debug(
                    "Function %s executed in %.2fms",
                    func.__name__,
                    duration,
                    extra={"duration_ms": duration}
                )
        return cast(T, wrapper)
    return decorator


def log_request():
    """Decorator to log HTTP request details."""
    def decorator(func: T) -> T:
        def wrapper(request, *args, **kwargs):
            logger = get_logger("http")
            request_id = RequestContext.get_request_id()
            
            # Log request start
            logger.info(
                "Request started",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client": request.client.host if request.client else None,
                    "request_id": request_id
                }
            )
            
            start_time = time.perf_counter()
            try:
                response = func(request, *args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000  # ms
                
                # Log successful response
                logger.info(
                    "Request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration,
                        "request_id": request_id
                    }
                )
                return response
                
            except Exception as e:
                duration = (time.perf_counter() - start_time) * 1000  # ms
                logger.error(
                    "Request failed",
                    exc_info=True,
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration,
                        "request_id": request_id,
                        "error": str(e)
                    }
                )
                raise
                
        return cast(T, wrapper)
    return decorator


# Initialize logging when module is imported
setup_sentry_logging()
configure_logging()
