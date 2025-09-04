"""
OpenTelemetry configuration for the application.
"""
import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from app.core.config import settings

logger = logging.getLogger(__name__)

def setup_opentelemetry(app):
    """Set up OpenTelemetry for the application."""
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info("OpenTelemetry OTLP endpoint not configured, skipping setup")
        return None

    try:
        # Configure the tracer provider
        provider = TracerProvider()
        
        # Only set up OTLP if endpoint is configured
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            # Configure OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
            
            # Add span processor to the tracer provider
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
        
        # Set the global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI if app is provided
        if app:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=provider,
                excluded_urls=settings.OTEL_PYTHON_EXCLUDED_URLS or ""
            )
        
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()
        
        # Instrument Redis if enabled
        if settings.REDIS_URL:
            RedisInstrumentor().instrument()
        
        # Instrument Logging
        LoggingInstrumentor().instrument(
            set_logging_format=True,
            log_level=settings.LOG_LEVEL
        )
        
        logger.info("OpenTelemetry configured successfully")
        return provider
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {str(e)}", exc_info=True)
        return None
