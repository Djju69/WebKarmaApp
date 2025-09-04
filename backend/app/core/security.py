"""
Security utilities for authentication and authorization.
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session
import redis
from ratelimit import limits, sleep_and_retry

from app.core.config import settings
from app.db.base import get_db
from app.models.user import User
from app.schemas.token import TokenData

# Initialize Redis for rate limiting and token blacklist
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def verify_token_blacklist(token: str) -> bool:
    """Check if token is blacklisted."""
    return bool(redis_client.get(f"blacklist:{token}"))


def add_token_to_blacklist(token: str, expire_seconds: int) -> None:
    """Add token to blacklist."""
    redis_client.setex(f"blacklist:{token}", expire_seconds, "blacklisted")


def create_verification_token(email: str, token_type: str = "verify") -> str:
    """Create an email verification or password reset token."""
    expires_delta = timedelta(minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": token_type
    }
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def verify_verification_token(token: str, token_type: str) -> Optional[str]:
    """Verify email verification or password reset token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.REFRESH_SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

@sleep_and_retry
@limits(calls=100, period=300)  # 100 calls per 5 minutes
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get the current authenticated user with rate limiting."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check token blacklist
    if verify_token_blacklist(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
            
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        raise credentials_exception from e
        
    # Rate limiting by IP and user ID
    ip = request.client.host
    user_attempts = redis_client.incr(f"auth_attempts:{ip}:{user_id}")
    if user_attempts > settings.MAX_AUTH_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": "900"},  # 15 minutes cooldown
        )
    
    # Reset counter after successful authentication
    if user_attempts > 0:
        redis_client.delete(f"auth_attempts:{ip}:{user_id}")
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
        
    # Check if email is verified
    if not user.is_verified and settings.REQUIRE_EMAIL_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address",
        )
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated"
        )
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def has_required_roles(user: User, required_roles: list[str]) -> bool:
    """Check if user has any of the required roles."""
    # In a real app, you would check the user's roles here
    # For now, we'll just check if the user is a superuser
    if user.is_superuser:
        return True
    
    # If no specific roles are required, allow access
    if not required_roles:
        return True
    
    # Check if user has any of the required roles
    # This is a placeholder - implement your own role checking logic
    user_roles = []  # Get user's roles from the database
    return any(role in user_roles for role in required_roles)
