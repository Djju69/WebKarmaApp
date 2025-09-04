"""
CRUD operations for User model.
"""
from typing import Any, Dict, Optional, Union, List
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.password import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User, UserRole, Role, Permission
from app.schemas.user import UserCreate, UserUpdate, UserWithRoles


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model with additional methods for authentication and authorization."""
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_telegram_id(self, db: Session, *, telegram_id: int) -> Optional[User]:
        """Get a user by Telegram ID."""
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()
    
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user with hashed password."""
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            hashed_password=get_password_hash(obj_in.password),
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """Update a user."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        # Handle password update
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        # Update fields from the input
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active
    
    def is_superuser(self, user: User) -> bool:
        """Check if user is a superuser."""
        return any(role.name == UserRole.SUPERADMIN for role in user.roles)
    
    def has_role(self, user: User, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role.name == role_name for role in user.roles)
    
    def has_permission(self, user: User, permission_name: str) -> bool:
        """Check if user has a specific permission."""
        # Superadmins have all permissions
        if self.is_superuser(user):
            return True
            
        # Check if any of the user's roles has the permission
        for role in user.roles:
            if any(permission.name == permission_name for permission in role.permissions):
                return True
        return False
        
    def update_backup_codes(self, db: Session, *, db_obj: User, backup_codes: List[str]) -> User:
        """Update user's backup codes for 2FA."""
        db_obj.backup_codes = backup_codes
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_last_login(self, db: Session, *, user: User) -> User:
        """Update the last login timestamp for a user."""
        user.last_login = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def update_profile(
        self, db: Session, *, db_obj: User, profile_data: Dict[str, Any]
    ) -> User:
        """Update user profile information."""
        update_data = {}
        
        # Only include fields that are allowed to be updated
        allowed_fields = ["first_name", "last_name", "phone_number", "email", "bio", "avatar_url"]
        
        for field in allowed_fields:
            if field in profile_data and profile_data[field] is not None:
                update_data[field] = profile_data[field]
        
        # Update fields
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


# Create a singleton instance
user = CRUDUser(User)
