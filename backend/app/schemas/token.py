"""
Token related schemas.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from app.core.config import settings


class Token(BaseModel):
    """Base token schema."""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    """
    JWT token payload schema.
    
    Attributes:
        sub: Subject (user identifier)
        exp: Expiration time (Unix timestamp)
        iat: Issued at time (Unix timestamp)
        jti: JWT ID (unique identifier for the token)
        type: Token type (e.g., 'access', 'refresh')
        scopes: List of scopes/token permissions
        2fa_verified: Whether 2FA verification was completed
    """
    sub: Optional[str] = Field(None, description="Subject (user identifier)")
    exp: Optional[int] = Field(None, description="Expiration time (Unix timestamp)")
    iat: Optional[int] = Field(None, description="Issued at time (Unix timestamp)")
    jti: Optional[str] = Field(None, description="JWT ID (unique identifier for the token)")
    type: Optional[str] = Field(None, description="Token type (e.g., 'access', 'refresh')")
    scopes: List[str] = Field(default_factory=list, description="List of scopes/token permissions")
    is_2fa_verified: Optional[bool] = Field(False, description="Whether 2FA verification was completed")


class TokenCreate(BaseModel):
    """Token creation schema."""
    email: str
    password: str


class TokenVerify(BaseModel):
    """Token verification schema."""
    token: str = Field(..., description="Verification token")


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, 
                         description="Password (8-128 characters)")
    username: str = Field(..., min_length=3, max_length=50, 
                         description="Username (3-50 characters, alphanumeric + _")
    first_name: Optional[str] = Field(None, max_length=50, 
                                    description="User's first name")
    last_name: Optional[str] = Field(None, max_length=50, 
                                   description="User's last name")

    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, 
                             description="New password (8-128 characters)")


class EmailVerification(BaseModel):
    """Email verification schema."""
    token: str = Field(..., description="Email verification token")


# TokenData is now deprecated in favor of TokenPayload
# which provides more comprehensive JWT token handling


class TokenResponse(BaseModel):
    """
    Token response schema with expiration and 2FA status.
    
    Attributes:
        access_token: JWT access token
        refresh_token: JWT refresh token
        token_type: Type of token (always "bearer")
        expires_in: Token expiration time in seconds
        requires_2fa: Whether 2FA verification is required
        is_2fa_verified: Whether the user has completed 2FA verification
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(
        int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        description="Token expiration time in seconds"
    )
    requires_2fa: bool = Field(
        False,
        description="Whether 2FA verification is required"
    )
    is_2fa_verified: bool = Field(
        False,
        description="Whether the user has completed 2FA verification"
    )
