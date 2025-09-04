"""
Pydantic models for roles and permissions.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class PermissionBase(BaseModel):
    """Base permission schema."""
    name: str = Field(..., description="Unique permission name (e.g., 'user:read')")
    description: Optional[str] = Field(None, description="Permission description")
    module: str = Field(..., description="Module this permission belongs to")

class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""
    pass

class Permission(PermissionBase):
    """Permission schema for responses."""
    id: int
    
    class Config:
        orm_mode = True

class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., description="Unique role name")
    description: Optional[str] = Field(None, description="Role description")
    is_system: bool = Field(False, description="Whether this is a system role")

class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    permission_ids: List[int] = Field(default_factory=list, description="List of permission IDs")

class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permission_ids: Optional[List[int]] = Field(None, description="List of permission IDs")

class Role(RoleBase):
    """Role schema for responses."""
    id: int
    permissions: List[Permission] = []
    
    class Config:
        orm_mode = True

class UserRoleAssignment(BaseModel):
    """Schema for assigning roles to users."""
    user_id: int
    role_ids: List[int] = Field(..., description="List of role IDs to assign to the user")

class UserPermissionResponse(BaseModel):
    """Schema for user permissions response."""
    user_id: int
    permissions: List[Permission]
