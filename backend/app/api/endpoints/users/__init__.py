"""
Users API endpoints.
"""
from fastapi import APIRouter

from . import profile

router = APIRouter()
router.include_router(profile.router, prefix="/profile", tags=["profile"])

__all__ = ["router"]
