"""
Token related schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Base token schema."""
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[int] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None


class TokenCreate(BaseModel):
    """Token creation schema."""
    email: str
    password: str


class TokenVerify(BaseModel):
    """Token verification schema."""
    token: str
