"""
Middleware package for API request processing.

This package contains middleware components for request validation,
error handling, and other cross-cutting concerns.
"""

from .validation_middleware import validate_request, ValidatedRoute

__all__ = [
    'validate_request',
    'ValidatedRoute',
]
