"""
User related schemas.
"""
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, constr, HttpUrl

from app.models.user import User as UserModel


# Constants for validation
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
NAME_MAX_LENGTH = 50
PHONE_MAX_LENGTH = 20

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address. Must be a valid email format.",
        example="user@example.com"
    )
    username: Optional[constr(
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        strip_whitespace=True,
        to_lower=True,
        pattern=r'^[a-zA-Z0-9_]+$'
    )] = Field(
        None,
        description=f"Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters long and can only contain letters, numbers, and underscores.",
        example="johndoe"
    )
    is_active: Optional[bool] = Field(
        True,
        description="Whether the user account is active. Inactive users cannot log in."
    )
    is_superuser: bool = Field(
        False,
        description="Whether the user has superuser privileges. Use with caution!"
    )
    first_name: Optional[constr(max_length=NAME_MAX_LENGTH)] = Field(
        None,
        description=f"User's first name. Maximum {NAME_MAX_LENGTH} characters.",
        example="John"
    )
    last_name: Optional[constr(max_length=NAME_MAX_LENGTH)] = Field(
        None,
        description=f"User's last name. Maximum {NAME_MAX_LENGTH} characters.",
        example="Doe"
    )
    phone: Optional[constr(max_length=PHONE_MAX_LENGTH)] = Field(
        None,
        description=f"User's phone number. Maximum {PHONE_MAX_LENGTH} characters.",
        example="+1234567890"
    )
    telegram_id: Optional[int] = Field(
        None,
        description="User's Telegram ID if linked with a Telegram account.",
        gt=0,
        example=123456789
    )
    preferred_language: Optional[constr(min_length=2, max_length=10)] = Field(
        "ru",
        description="User's preferred language code (ISO 639-1). Default is 'ru'.",
        example="ru"
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""
    email: EmailStr = Field(
        ...,
        description="User's email address. Must be a valid and unique email.",
        example="user@example.com"
    )
    password: constr(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH
    ) = Field(
        ...,
        description=f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters long and include at least one uppercase letter, one lowercase letter, one number, and one special character.",
        example="SecurePass123!"
    )
    username: constr(
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        strip_whitespace=True,
        to_lower=True,
        pattern=r'^[a-zA-Z0-9_]+$'
    ) = Field(
        ...,
        description=f"Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters long and can only contain letters, numbers, and underscores.",
        example="johndoe"
    )
    role_ids: Optional[List[int]] = Field(
        None,
        description="List of role IDs to assign to the user.",
        example=[1, 2]
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f'Password must be at least {PASSWORD_MIN_LENGTH} characters long')
        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValueError(f'Password must not exceed {PASSWORD_MAX_LENGTH} characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Validate email domain."""
        # Example: Block disposable email domains
        disposable_domains = {'yopmail.com', 'mailinator.com', 'tempmail.com'}
        domain = v.split('@')[-1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        return v


class UserUpdate(UserBase):
    """Schema for updating an existing user."""
    password: Optional[constr(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)] = Field(
        None,
        description=f"New password. If provided, must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters long and meet complexity requirements.",
        example="NewSecurePass123!"
    )
    current_password: Optional[str] = Field(
        None,
        description="Current password is required when changing the password.",
        example="CurrentPass123!"
    )
    role_ids: Optional[List[int]] = Field(
        None,
        description="List of role IDs to update user's roles. If provided, replaces all existing roles.",
        example=[1, 2]
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_change(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate password change requirements."""
        if v is not None and not info.data.get('current_password'):
            raise ValueError('Current password is required to change the password')
        return v
    
    @model_validator(mode='after')
    def validate_update_fields(self) -> 'UserUpdate':
        """Validate that at least one field is being updated."""
        data = self.model_dump(exclude_unset=True)
        if not any(k in data for k in self.model_fields if k not in ('password', 'current_password')):
            raise ValueError('At least one field must be provided for update')
        return self


class UserInDBBase(UserBase):
    """Base schema for user in database."""
    id: int
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class User(UserInDBBase):
    """User schema for API responses."""
    pass


class UserInDB(UserInDBBase):
    """User schema for internal use with hashed password."""
    hashed_password: str


class UserWithRoles(User):
    """User schema with roles included."""
    roles: List[str] = []
    
    @classmethod
    def from_orm(cls, user: UserModel):
        """Convert SQLAlchemy model to Pydantic model with roles."""
        user_dict = user.__dict__.copy()
        user_dict['roles'] = [role.name for role in user.roles]
        return cls(**user_dict)
