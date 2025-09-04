"""
Main API router that includes all the endpoint routers.
"""
from fastapi import APIRouter

from app.core.config import settings

# Import all endpoint routers
from app.api.endpoints import auth, users, cache, two_factor_router

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)

# Include user management endpoints
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

# Include 2FA endpoints
api_router.include_router(
    two_factor_router,
    prefix="/2fa",
    tags=["2FA"]
)

# Include cache endpoints
api_router.include_router(
    cache.router,
    prefix="/cache",
    tags=["cache"]
)

# Include new 2FA endpoints
api_router.include_router(
    two_factor_router,
    prefix="/2fa",
    tags=["2FA"]
)
