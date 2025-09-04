"""
Profile related schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, constr, EmailStr, validator

# Constants for validation
NAME_MAX_LENGTH = 50
PHONE_MAX_LENGTH = 20
BIO_MAX_LENGTH = 500

class ProfileBase(BaseModel):
    """Base profile schema with common fields."""
    first_name: Optional[constr(max_length=NAME_MAX_LENGTH)] = Field(
        None,
        description="User's first name.",
        example="John"
    )
    last_name: Optional[constr(max_length=NAME_MAX_LENGTH)] = Field(
        None,
        description="User's last name.",
        example="Doe"
    )
    phone: Optional[constr(max_length=PHONE_MAX_LENGTH)] = Field(
        None,
        description="User's phone number.",
        example="+1234567890"
    )
    bio: Optional[constr(max_length=BIO_MAX_LENGTH)] = Field(
        None,
        description="User's biography or description.",
        example="Software developer with 5+ years of experience."
    )
    avatar_url: Optional[str] = Field(
        None,
        description="URL to user's avatar image.",
        example="https://example.com/avatars/johndoe.jpg"
    )

class ProfileUpdate(ProfileBase):
    """Schema for updating user profile."""
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address. Must be a valid email format.",
        example="user@example.com"
    )

    @validator('phone')
    def validate_phone(cls, v):
        if v is not None and not v.startswith('+'):
            raise ValueError('Phone number must start with a plus sign (+)')
        return v

class ProfileResponse(ProfileBase):
    """Profile response schema."""
    email: EmailStr
    is_email_verified: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "user@example.com",
                "phone": "+1234567890",
                "bio": "Software developer with 5+ years of experience.",
                "avatar_url": "https://example.com/avatars/johndoe.jpg",
                "is_email_verified": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
