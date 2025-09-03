"""
User management endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.rbac import RBAC
from app.core.security import get_password_hash
from app.db.base import get_db
from app.models.user import User, Role
from app.models.audit_log import ActionType
from app.schemas.user import UserCreate, UserUpdate, User as UserSchema, UserWithRoles
from app.services.audit_service import AuditService, get_audit_service

# Add new action type for viewing user details
ActionType.USER_VIEW_DETAILS = "user_view_details"

router = APIRouter()

@router.get("/", response_model=List[UserSchema])
@RBAC.has_role(["admin"])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_role(["admin"]))
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
@RBAC.has_role(["admin"])
async def create_user(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_role(["admin"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Create a new user (admin only)."""
    # Check if user with email already exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if user with username already exists
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        is_active=user_in.is_active,
    )
    
    # Add roles if provided
    if user_in.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_in.role_ids)).all()
        db_user.roles = roles
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log the action
    await audit_service.log(
        action=ActionType.USER_CREATE,
        request=request,
        user=current_user,
        resource_type="user",
        resource_id=str(db_user.id),
        details={
            "email": db_user.email,
            "username": db_user.username,
            "is_active": db_user.is_active,
            "role_ids": user_in.role_ids
        }
    )
    
    return db_user

@router.get("/me", response_model=UserWithRoles)
async def read_user_me(
    request: Request,
    current_user: User = Depends(RBAC.has_role([])),  # Any authenticated user
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Get current user information."""
    # Eager load roles and permissions
    user = db.query(User).filter(User.id == current_user.id).first()
    
    # Log the action
    await audit_service.log(
        action=ActionType.USER_VIEW,
        request=request,
        user=current_user,
        resource_type="user",
        resource_id=str(user.id)
    )
    
    return user

@router.get("/{user_id}", response_model=UserWithRoles)
@RBAC.has_role(["admin"])
async def read_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_role(["admin"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Get user by ID (admin only)."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log the action
    await audit_service.log(
        action=ActionType.USER_VIEW,
        request=request,
        user=current_user,
        resource_type="user",
        resource_id=str(user_id)
    )
    
    return db_user

@router.put("/{user_id}", response_model=UserSchema)
@RBAC.has_role(["admin"])
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_role(["admin"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Update a user (admin only)."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user data
    update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    if "role_ids" in update_data:
        roles = db.query(Role).filter(Role.id.in_(update_data.pop("role_ids"))).all()
        db_user.roles = roles
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@RBAC.has_role(["admin"])
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_role(["admin"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Delete a user (admin only)."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Get user data for audit log before deletion
    user_data = {
        "email": db_user.email,
        "username": db_user.username,
        "is_active": db_user.is_active,
        "role_ids": [role.id for role in db_user.roles]
    }
    
    db.delete(db_user)
    db.commit()
    
    # Log the action
    await audit_service.log(
        action=ActionType.USER_DELETE,
        request=request,
        user=current_user,
        resource_type="user",
        resource_id=str(user_id),
        details=user_data
    )
    
    return None
