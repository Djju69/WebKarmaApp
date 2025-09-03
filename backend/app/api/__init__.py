"""
API package for WebKarmaApp.

This package contains all API endpoints and related functionality.
"""

# API version
__version__ = "0.1.0"

# Import all endpoint modules to register them with the router
from . import endpoints  # noqa

__all__ = [
    'endpoints',
]
