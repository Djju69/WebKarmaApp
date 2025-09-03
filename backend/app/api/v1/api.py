"""
API v1 router configuration.
"""
from fastapi import APIRouter

# Import all endpoint modules
from .endpoints import telegram

# Create API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    telegram.router,
    prefix="/telegram",
    tags=["telegram"]
)

# Example of including other routers
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(items.router, prefix="/items", tags=["items"])
