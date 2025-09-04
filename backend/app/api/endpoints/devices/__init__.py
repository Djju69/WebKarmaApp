"""
Device management API endpoints.
"""
from fastapi import APIRouter

from app.api.endpoints.devices import views

# Create router
router = APIRouter()

# Include device management endpoints
router.include_router(
    views.router,
    prefix="",
    tags=["devices"]
)
