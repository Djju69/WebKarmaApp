"""
Profile management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict

from app import crud, models, schemas
from app.api import deps
from app.core.security import get_current_active_user
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter()

@router.get("/me", response_model=ProfileResponse)
async def read_profile(
    current_user: models.User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user profile.
    """
    return current_user

@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    *,
    db: Session = Depends(deps.get_db),
    profile_in: ProfileUpdate,
    current_user: models.User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user profile.
    """
    # Check if email is being updated and if it's already taken
    if profile_in.email and profile_in.email != current_user.email:
        user = crud.user.get_by_email(db, email=profile_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже зарегистрирован в системе.",
            )
    
    # Convert Pydantic model to dict and remove None values
    update_data = profile_in.dict(exclude_unset=True)
    
    # Update user profile
    user = crud.user.update_profile(db, db_obj=current_user, profile_data=update_data)
    return user

@router.get("/me/avatar-upload-url", response_model=Dict[str, Any])
async def get_avatar_upload_url(
    current_user: models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get a pre-signed URL for uploading an avatar.
    """
    # TODO: Implement pre-signed URL generation for file upload
    # This is a placeholder implementation
    return {
        "url": "https://api.example.com/upload-avatar",
        "fields": {
            "key": f"avatars/{current_user.id}/${{filename}}",
            "Content-Type": "image/*",
            "success_action_status": "201",
        },
        "method": "POST",
    }
