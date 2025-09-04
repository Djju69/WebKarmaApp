"""
API v1 router configuration.
"""
from fastapi import APIRouter

# Import all endpoint modules
from .endpoints import telegram
from ..endpoints import auth, users, roles, devices

# Create API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    telegram.router,
    prefix="/telegram",
    tags=["telegram"]
)

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)

# User management endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Device management endpoints
api_router.include_router(
    devices.router,
    prefix="/devices",
    tags=["devices"]
)

# Role and permission management endpoints
api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["roles"]
)
