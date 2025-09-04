"""
Roles and permissions management endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.rbac import RBAC
from app.db.base import get_db
from app.models.user import Role, Permission, User, user_roles, role_permissions
from app.schemas.role import RoleCreate, RoleUpdate, Role as RoleSchema, Permission as PermissionSchema
from app.services.audit_service import AuditService, get_audit_service

router = APIRouter()

# Permissions management
@router.get("/permissions/", response_model=List[PermissionSchema])
@RBAC.has_permission(["permission:read"])
async def list_permissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["permission:read"]))
):
    """List all available permissions (requires permission:read)."""
    permissions = db.query(Permission).offset(skip).limit(limit).all()
    return permissions

# Roles management
@router.get("/", response_model=List[RoleSchema])
@RBAC.has_permission(["role:read"])
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["role:read"]))
):
    """List all roles (requires role:read permission)."""
    roles = db.query(Role).offset(skip).limit(limit).all()
    return roles

@router.post("/", response_model=RoleSchema, status_code=status.HTTP_201_CREATED)
@RBAC.has_permission(["role:create"])
async def create_role(
    request: Request,
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["role:create"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Create a new role (requires role:create permission)."""
    # Check if role with name already exists
    db_role = db.query(Role).filter(Role.name == role_in.name).first()
    if db_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )
    
    # Create new role
    role = Role(
        name=role_in.name,
        description=role_in.description,
        is_system=False  # System roles are created by the system only
    )
    
    # Add permissions if any
    if role_in.permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        role.permissions = permissions
    
    try:
        db.add(role)
        db.commit()
        db.refresh(role)
        
        # Log the action
        await audit_service.log_action(
            user_id=current_user.id,
            action_type="role_create",
            resource_type="role",
            resource_id=role.id,
            details={"role_name": role.name}
        )
        
        return role
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating role"
        )

@router.get("/{role_id}", response_model=RoleSchema)
@RBAC.has_permission(["role:read"])
async def read_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["role:read"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Get role by ID (requires role:read permission)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Log the action
    await audit_service.log_action(
        user_id=current_user.id,
        action_type="role_view",
        resource_type="role",
        resource_id=role.id,
        details={"role_name": role.name}
    )
    
    return role

@router.put("/{role_id}", response_model=RoleSchema)
@RBAC.has_permission(["role:update"])
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["role:update"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Update a role (requires role:update permission)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent modifying system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system roles"
        )
    
    # Update role fields
    if role_in.name is not None:
        # Check if name is already taken
        existing = db.query(Role).filter(Role.name == role_in.name, Role.id != role_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role with this name already exists"
            )
        role.name = role_in.name
    
    if role_in.description is not None:
        role.description = role_in.description
    
    # Update permissions if provided
    if role_in.permission_ids is not None:
        permissions = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        role.permissions = permissions
    
    try:
        db.add(role)
        db.commit()
        
        # Log the action
        await audit_service.log_action(
            user_id=current_user.id,
            action_type="role_update",
            resource_type="role",
            resource_id=role.id,
            details={"role_name": role.name}
        )
        
        return role
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating role"
        )

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@RBAC.has_permission(["role:delete"])
async def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(RBAC.has_permission(["role:delete"])),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Delete a role (requires role:delete permission)."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Prevent deleting system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system roles"
        )
    
    # Check if role is assigned to any user
    user_count = db.query(user_roles).filter(user_roles.c.role_id == role_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to users"
        )
    
    try:
        # Log the action before deleting
        await audit_service.log_action(
            user_id=current_user.id,
            action_type="role_delete",
            resource_type="role",
            resource_id=role.id,
            details={"role_name": role.name}
        )
        
        # Delete role-permission associations
        db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
        
        # Delete the role
        db.delete(role)
        db.commit()
        
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting role"
        )
