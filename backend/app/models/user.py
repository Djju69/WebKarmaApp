"""
User model for the loyalty system with RBAC and multi-language support.
"""
from datetime import datetime
from typing import List
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

class UserRole(str, Enum):
    USER = 'user'
    PARTNER = 'partner'
    ADMIN = 'admin'
    SUPERADMIN = 'superadmin'

class User(Base):
    """User model with RBAC and multi-language support."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)  # Nullable for web users
    username = Column(String(64), index=True, nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)  # For web authentication
    is_active = Column(Boolean(), default=True)
    is_verified = Column(Boolean(), default=False)  # Email verification
    preferred_language = Column(String(10), default='ru')  # ru, en, es, fr
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loyalty_accounts = relationship("LoyaltyAccount", back_populates="user", lazy="selectin")
    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="selectin")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="selectin")
    # This is a hybrid property to get all permissions through roles
    @property
    def user_permissions(self):
        """Get all permissions for the user through their roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(role.permissions)
        return list(permissions)

    def __repr__(self):
        return f"<User {self.id} ({self.email or self.telegram_id or 'No identifier'})>"

    @property
    def full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id or self.email)

    def has_role(self, role_name: str) -> bool:
        """Check if user has the specified role."""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has the specified permission."""
        # Superadmins have all permissions
        if self.has_role('superadmin'):
            return True
            
        # Check user's roles for the permission
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        return False


class Role(Base):
    """Role model for RBAC system."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False)  # System roles cannot be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(Base):
    """Permission model for RBAC system."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    module = Column(String(50), nullable=False)  # e.g., 'admin', 'content', 'billing'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.name} ({self.module})>"
