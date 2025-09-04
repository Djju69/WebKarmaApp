"""
Security utilities for authentication and authorization, including 2FA.
"""
import asyncio
import base64
import hashlib
import io
import pyotp
import qrcode
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from ratelimit import limits, sleep_and_retry
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import user as user_crud
from app.db.base import get_db
from app.models.user import User
from app.schemas.token import TokenPayload as TokenData
from app.schemas.two_factor import TwoFactorSetupResponse, TwoFactorVerifyRequest

# Initialize Redis for rate limiting and token blacklist
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# ===== 2FA Functions =====

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()

def generate_totp_uri(email: str, secret: str) -> str:
    """Generate TOTP URI for QR code generation."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=settings.PROJECT_NAME
    )

def generate_qr_code(uri: str) -> str:
    """Generate a base64-encoded QR code image from URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code against a secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=window)

def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate a list of backup codes."""
    return [
        f"{random.randint(100000, 999999)}-{random.randint(100000, 999999)}"
        for _ in range(count)
    ]

def setup_2fa_for_user(db: Session, user: User) -> TwoFactorSetupResponse:
    """Set up 2FA for a user."""
    if user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already set up for this user"
        )
    
    # Generate new secret and backup codes
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    
    # Update user with new secret and backup codes
    user = user_crud.user.update_2fa_secret(
        db, db_obj=user, secret=secret, backup_codes=backup_codes
    )
    
    # Generate provisioning URI and QR code
    uri = generate_totp_uri(user.email, secret)
    qr_code = generate_qr_code(uri)
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes,
        message="Scan the QR code with an authenticator app"
    )

def verify_2fa_code(db: Session, user: User, code: str) -> bool:
    """Verify a 2FA code for a user."""
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not set up for this user"
        )
    
    # Check backup codes first
    if user.backup_codes and code in user.backup_codes:
        # Remove used backup code
        backup_codes = [c for c in user.backup_codes if c != code]
        user = user_crud.user.update_backup_codes(db, db_obj=user, backup_codes=backup_codes)
        return True
    
    # Check TOTP code
    if verify_totp_code(user.totp_secret, code):
        return True
    
    return False

def enable_2fa_for_user(db: Session, user: User, code: str) -> None:
    """Enable 2FA for a user after verifying the first code."""
    if user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled for this user"
        )
    
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA secret not found. Please set up 2FA first."
        )
    
    if not verify_2fa_code(db, user, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    user_crud.user.enable_2fa(db, db_obj=user)

def disable_2fa_for_user(db: Session, user: User) -> None:
    """Disable 2FA for a user."""
    user_crud.user.disable_2fa(db, db_obj=user)

def regenerate_backup_codes(db: Session, user: User) -> list[str]:
    """Regenerate backup codes for a user."""
    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not set up for this user"
        )
    
    backup_codes = generate_backup_codes()
    user = user_crud.user.update_backup_codes(db, db_obj=user, backup_codes=backup_codes)
    return backup_codes

# Import password utilities
from .password import verify_password, get_password_hash
from app.crud import user as user_crud


def verify_token_blacklist(token: str) -> bool:
    """
    Check if a JWT token is blacklisted by its jti claim or raw token value.
    
    This function checks if a token has been explicitly blacklisted in Redis,
    either by its unique JWT ID (jti) or by its raw token value.
    
    Args:
        token: The JWT token to check against the blacklist
        
    Returns:
        bool: 
            - True if the token or its jti is found in the blacklist
            - False if the token is not blacklisted or an error occurs
            
    Example:
        if verify_token_blacklist(token):
            raise HTTPException(401, "This token has been revoked")
    """
    if not token or not isinstance(token, str):
        return False
        
    try:
        # Try to get the jti from the token without full validation
        try:
            # Decode without verification to get the jti
            unverified = jwt.get_unverified_claims(token)
            jti = unverified.get("jti")
            
            # Check if the jti is in the blacklist
            if jti and redis_client.exists(f"token_blacklist:{jti}"):
                print(f"Token with jti {jti} is blacklisted")
                return True
        except JWTError as e:
            # If we can't get the jti, we'll check the raw token
            pass
        
        # Fall back to checking the raw token (useful for tokens without jti)
        if redis_client.exists(f"token_blacklist_raw:{token}"):
            print(f"Raw token is blacklisted")
            return True
        
        # Also check for token family (useful for refresh token rotation)
        if "jti" in locals() and jti:
            # Check if any token in the same family is blacklisted
            family_key = f"token_family:{jti.split('-')[0]}"
            if redis_client.exists(family_key):
                print(f"Token family {family_key} is blacklisted")
                return True
                
        return False
        
    except redis.RedisError as e:
        # If Redis is down, we should fail securely by treating all tokens as invalid
        print(f"Redis error in verify_token_blacklist: {str(e)}")
        return True  # Fail secure - treat as blacklisted
        
    except Exception as e:
        # Log other errors but don't block the request
        print(f"Error in verify_token_blacklist: {str(e)}")
        return False


def add_token_to_blacklist(token: str, expire_seconds: int = None) -> bool:
    """
    Add a JWT token to the blacklist to prevent its further use.
    
    This function adds a token to the blacklist using both its jti claim (if available)
    and its raw value. The blacklist entry will expire after the specified duration.
    
    Args:
        token: The JWT token to blacklist
        expire_seconds: Number of seconds until the blacklist entry expires.
                      If None, uses default from settings or calculates based on token expiration.
                      
    Returns:
        bool: True if the token was successfully blacklisted, False otherwise
        
    Example:
        # Blacklist a token for 1 hour
        success = add_token_to_blacklist(token, expire_seconds=3600)
    """
    if not token or not isinstance(token, str):
        return False
        
    if expire_seconds is None:
        # Default to 7 days if not specified
        expire_seconds = 60 * 60 * 24 * 7
        
        # Try to get expiration from the token itself
        try:
            unverified = jwt.get_unverified_claims(token)
            exp = unverified.get("exp")
            if exp:
                # Set expiration to token's remaining lifetime + 1 hour buffer
                remaining = exp - int(time.time())
                if remaining > 0:
                    expire_seconds = remaining + 3600  # Add 1 hour buffer
        except Exception:
            pass
    
    try:
        # Decode the token to get the jti
        jti = None
        token_family = None
        
        try:
            unverified = jwt.get_unverified_claims(token)
            jti = unverified.get("jti")
            
            # Extract token family (first part of UUID)
            if jti and '-' in jti:
                token_family = f"token_family:{jti.split('-')[0]}"
        except JWTError as e:
            # If we can't decode the token, we'll just blacklist the raw value
            pass
        
        # Start a Redis pipeline for atomic operations
        with redis_client.pipeline() as pipe:
            # Blacklist by jti if available
            if jti:
                pipe.setex(
                    f"token_blacklist:{jti}",
                    expire_seconds,
                    "blacklisted"
                )
                
                # Also add to token family blacklist if available
                if token_family:
                    pipe.setex(
                        token_family,
                        expire_seconds,
                        "blacklisted"
                    )
            
            # Always blacklist the raw token as a fallback
            pipe.setex(
                f"token_blacklist_raw:{token}",
                expire_seconds,
                "blacklisted"
            )
            
            # Execute all operations atomically
            pipe.execute()
            
        return True
        
    except redis.RedisError as e:
        print(f"Redis error adding token to blacklist: {str(e)}")
        return False
    except Exception as e:
        print(f"Error adding token to blacklist: {str(e)}")
        return False


def create_verification_token(email: str, token_type: str = "verify") -> str:
    """
    Create a JWT token for email verification, password reset, or other verifications.
    
    This function generates a time-limited token that can be used for one-time
    verification purposes like email confirmation, password resets, etc.
    
    Args:
        email: The email address to associate with this token
        token_type: Type of verification token. Common types:
                   - 'verify': Email verification
                   - 'password_reset': Password reset
                   - 'email_change': Email change confirmation
                   - '2fa_backup': 2FA backup code
                   
    Returns:
        str: A signed JWT token with standard claims
        
    Raises:
        ValueError: If email is invalid or token_type is not specified
        
    Example:
        # Create a password reset token
        token = create_verification_token("user@example.com", "password_reset")
    """
    if not email or "@" not in email:
        raise ValueError("Invalid email address")
        
    if not token_type:
        raise ValueError("Token type is required")
    
    # Normalize email to lowercase
    email = email.lower().strip()
    
    # Set expiration time based on token type
    now = datetime.utcnow()
    
    # Different expiration times for different token types
    if token_type == "password_reset":
        # Shorter expiration for password reset (1 hour)
        expires_delta = timedelta(hours=1)
    elif token_type == "2fa_backup":
        # Longer expiration for 2FA backup codes (30 days)
        expires_delta = timedelta(days=30)
    else:
        # Default expiration (24 hours)
        expires_delta = timedelta(hours=24)
    
    expire = now + expires_delta
    jti = str(uuid.uuid4())
    
    # Standard JWT claims + custom claims
    to_encode = {
        # Standard claims
        "iss": settings.PROJECT_NAME,  # Issuer
        "sub": email,                 # Subject (email)
        "exp": expire,                # Expiration time
        "iat": now,                   # Issued at
        "jti": jti,                   # JWT ID (for token revocation)
        
        # Custom claims
        "type": token_type,           # Token type
        "scope": "verification",      # Token scope
        "version": "1.0"              # Token version (for future compatibility)
    }
    
    # Add token-type specific claims
    if token_type == "password_reset":
        to_encode["purpose"] = "password_reset"
    
    try:
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    except Exception as e:
        # Log the error (in production, use proper logging)
        print(f"Failed to create verification token: {str(e)}")
        raise


def verify_verification_token(token: str, token_type: str) -> Optional[str]:
    """
    Verify an email verification or password reset token.
    
    This function validates a JWT token used for email verification, password reset,
    or other one-time verification purposes. It checks the token signature, expiration,
    and expected claims.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type (e.g., 'verify', 'reset', 'password_reset')
        
    Returns:
        Optional[str]: 
            - The email address from the token if verification is successful
            - None if the token is invalid, expired, or doesn't match the expected type
            
    Example:
        # Verify a password reset token
        email = verify_verification_token(token, 'password_reset')
        if not email:
            raise HTTPException(400, "Invalid or expired token")
    """
    if not token or not isinstance(token, str):
        return None
        
    try:
        # Decode and validate the token with standard JWT claims
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "require": ["exp", "iat", "sub", "type", "jti", "iss", "scope"],
                "verify_iss": True,
                "verify_aud": False,
                "verify_sub": True,
                "verify_iat": True,
                "verify_exp": True,
                "leeway": 30  # 30 seconds leeway for clock skew
            },
            issuer=settings.PROJECT_NAME
        )
        
        # Check if token is blacklisted (prevent reuse)
        if verify_token_blacklist(token):
            print(f"Blocked blacklisted token: {payload.get('jti')}")
            return None
        
        # Verify token type matches expected type
        if payload.get("type") != token_type:
            print(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None
            
        # Verify token scope is for verification
        if payload.get("scope") != "verification":
            print(f"Invalid token scope: {payload.get('scope')}")
            return None
            
        # Get and validate the subject (email)
        email: str = payload.get("sub", "").strip()
        if not email or "@" not in email:
            print(f"Invalid email in token: {email}")
            return None
            
        # Additional validation for specific token types
        if token_type == "password_reset":
            # Ensure the token was issued recently (e.g., last 24 hours)
            issued_at = payload.get("iat")
            if issued_at and (datetime.utcnow().timestamp() - issued_at) > 24 * 3600:
                print("Password reset token expired (older than 24 hours)")
                return None
            
        return email.lower()  # Normalize email case
        
    except jwt.ExpiredSignatureError:
        print(f"Token expired: {token_type} token")
        return None
    except jwt.JWTClaimsError as e:
        print(f"Invalid token claims: {str(e)}")
        return None
    except jwt.JWTError as e:
        # Log the error for debugging (in production, use proper logging)
        print(f"Token verification failed: {str(e)}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error verifying token: {str(e)}")
        return None


def add_token_to_blacklist(token: str, expire_seconds: int = 3600) -> bool:
    """
    Add a JWT token to the blacklist to prevent reuse.
    
    This function adds the token to Redis with a TTL (time to live) to automatically
    remove it after a certain period.
    
    Args:
        token: The JWT token to blacklist
        expire_seconds: Optional expiration time in seconds (default: 3600, 1 hour)
        
    Returns:
        bool: True if the token was successfully added to the blacklist, False otherwise
    """
    try:
        # Use Redis pipeline to execute multiple commands atomically
        with redis_client.pipeline() as pipe:
            # Add token to blacklist with TTL
            pipe.setex(
                f"token_blacklist:{token}",
                expire_seconds,
                "blacklisted"
            )
            
            # Always blacklist the raw token as a fallback
            pipe.setex(
                f"token_blacklist_raw:{token}",
                expire_seconds,
                "blacklisted"
            )
            
            # Execute all operations atomically
            pipe.execute()
            
        return True
        
    except redis.RedisError as e:
        print(f"Redis error adding token to blacklist: {str(e)}")
        return False
    except Exception as e:
        print(f"Error adding token to blacklist: {str(e)}")
        return False


def verify_token_blacklist(token: str) -> bool:
    """
    Check if a JWT token is blacklisted.
    
    This function checks if the token is present in the Redis blacklist.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        bool: True if the token is blacklisted, False otherwise
    """
    try:
        # Check if token is blacklisted
        return redis_client.exists(f"token_blacklist:{token}") == 1
    except redis.RedisError as e:
        print(f"Redis error verifying token blacklist: {str(e)}")
        return False
    except Exception as e:
        print(f"Error verifying token blacklist: {str(e)}")
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    is_2fa_verified: bool = False,
    jti: Optional[str] = None,
    scope: str = "access",
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    **additional_claims: Any
) -> str:
    """
    Create a secure JWT access token with enhanced security features.
    
    This function generates an access token with standard claims, token binding,
    and support for 2FA verification status.
    
    Args:
        data: Token payload data (must include 'sub' claim)
        expires_delta: Optional expiration time delta. If not provided,
                     uses ACCESS_TOKEN_EXPIRE_MINUTES from settings.
        is_2fa_verified: Whether 2FA verification was completed
        jti: Optional JWT ID (if not provided, a random UUID will be generated)
        scope: Token scope (e.g., 'access', 'api')
        user_agent: Optional user agent string for token binding
        ip_address: Optional IP address for token binding
        **additional_claims: Additional claims to include in the token
        
    Returns:
        str: Encoded JWT access token with standard and security claims
        
    Raises:
        ValueError: If required data is missing or invalid
        
    Example:
        token = create_access_token(
            data={"sub": "user@example.com"},
            expires_delta=timedelta(minutes=15),
            is_2fa_verified=True,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host
        )
    """
    if not data or 'sub' not in data:
        raise ValueError("Token data must include 'sub' claim")
    
    # Generate a new JWT ID if not provided
    jti = jti or str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Set expiration time with some randomness to prevent token clustering
    if not expires_delta:
        # Add some randomness to expiration to prevent token clustering
        random_minutes = random.randint(-5, 5)  # ±5 minutes
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + random_minutes
        )
    
    expire = now + expires_delta
    
    # Standard JWT claims for access token
    token_data = {
        # Standard claims (https://tools.ietf.org/html/rfc7519#section-4.1)
        "iss": settings.PROJECT_NAME,  # Issuer
        "sub": str(data['sub']),       # Subject (user identifier)
        "exp": expire,                 # Expiration Time
        "nbf": now,                    # Not Before
        "iat": now,                    # Issued At
        "jti": jti,                    # JWT ID
        
        # Custom claims
        "type": "access",              # Token type
        "scope": scope,                # Token scope
        "2fa_verified": is_2fa_verified, # 2FA verification status
        "version": "1.0",              # Token version for future compatibility
        
        # Security claims
        "aud": ["web"],                # Audience
        "azp": settings.PROJECT_NAME,   # Authorized party
    }
    
    # Add token binding claims if available
    if user_agent:
        token_data["ua"] = hashlib.sha256(user_agent.encode()).hexdigest()
    if ip_address:
        token_data["ip"] = hashlib.sha256(ip_address.encode()).hexdigest()
    
    # Add additional claims from data (overriding any standard claims)
    token_data.update({
        k: v for k, v in data.items() 
        if k not in token_data and not k.startswith('_')
    })
    
    # Add any additional claims provided as keyword arguments
    token_data.update(additional_claims)
    
    try:
        return jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            headers={
                "kid": "1",  # Key ID (for key rotation)
                "typ": "JWT",
                "alg": settings.ALGORITHM
            }
        )
    except Exception as e:
        print(f"Error creating access token: {str(e)}")
        raise


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
    scope: str = "refresh",
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    rotation_enabled: bool = True
) -> str:
    """
    Create a secure JWT refresh token with enhanced security features.
    
    This function generates a refresh token with standard claims, token binding,
    and support for token rotation to prevent token reuse.
    
    Args:
        data: Token payload data (must include 'sub' claim)
        expires_delta: Optional expiration time delta. If not provided,
                     uses REFRESH_TOKEN_EXPIRE_DAYS from settings.
        jti: Optional JWT ID (if not provided, a random UUID will be generated)
        scope: Token scope (e.g., 'refresh', 'offline_access')
        user_agent: Optional user agent string for token binding
        ip_address: Optional IP address for token binding
        rotation_enabled: Whether to enable token rotation (prevents reuse)
        
    Returns:
        str: Encoded JWT refresh token with standard and security claims
        
    Raises:
        ValueError: If required data is missing or invalid
        
    Example:
        token = create_refresh_token(
            data={"sub": "user@example.com"},
            expires_delta=timedelta(days=30),
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host
        )
    """
    if not data or 'sub' not in data:
        raise ValueError("Token data must include 'sub' claim")
    
    # Generate a new JWT ID and family ID for token rotation
    jti = jti or str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Set expiration time with some randomness to prevent token clustering
    if not expires_delta:
        # Add some randomness to expiration to prevent token clustering
        random_days = random.randint(-1, 1)  # ±1 day
        expires_delta = timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS + random_days
        )
    
    expire = now + expires_delta
    
    # Standard JWT claims for refresh token
    token_data = {
        # Standard claims (https://tools.ietf.org/html/rfc7519#section-4.1)
        "iss": settings.PROJECT_NAME,  # Issuer
        "sub": str(data['sub']),       # Subject (user identifier)
        "exp": expire,                 # Expiration Time
        "nbf": now,                    # Not Before
        "iat": now,                    # Issued At
        "jti": jti,                    # JWT ID
        
        # Custom claims
        "type": "refresh",             # Token type
        "scope": scope,                # Token scope
        "2fa_verified": False,         # Refresh tokens don't carry 2FA status
        "version": "1.0",              # Token version for future compatibility
        
        # Security claims
        "aud": ["web"],                # Audience
        "azp": settings.PROJECT_NAME,   # Authorized party
        "token_family": family_id,      # For token rotation
        "rotatable": rotation_enabled,  # Whether this token can be rotated
    }
    
    # Add token binding claims if available
    if user_agent:
        token_data["ua"] = hashlib.sha256(user_agent.encode()).hexdigest()
    if ip_address:
        token_data["ip"] = hashlib.sha256(ip_address.encode()).hexdigest()
    
    # Add custom claims from input data (overriding any standard claims)
    token_data.update({
        k: v for k, v in data.items() 
        if k not in token_data and not k.startswith('_')
    })
    
    try:
        return jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            headers={
                "kid": "1",  # Key ID (for key rotation)
                "typ": "JWT",
                "alg": settings.ALGORITHM
            }
        )
    except Exception as e:
        print(f"Error creating refresh token: {str(e)}")
        raise


@sleep_and_retry
@limits(calls=100, period=300)  # 100 calls per 5 minutes
async def get_current_user(
    request: Request,
    require_2fa: bool = True,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current authenticated user with rate limiting and 2FA verification.
    
    This function validates the JWT token, checks rate limiting, verifies the token
    is not blacklisted, and enforces 2FA verification if required.
    
    Args:
        request: FastAPI request object
        require_2fa: Whether to require 2FA verification
        db: Database session
        token: JWT token from Authorization header
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails or 2FA is required but not verified
    """
    # Rate limiting check (10 requests per minute per IP)
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:{client_ip}"
    
    # Check if IP is rate limited
    current = redis_client.get(rate_limit_key)
    if current and int(current) > 10:  # Allow 10 requests per minute
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    # Increment rate limit counter
    with redis_client.pipeline() as pipe:
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, 60)  # Reset counter after 60 seconds
        pipe.execute()
    
    # Check if token is blacklisted
    if verify_token_blacklist(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Define authentication error response
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Decode and validate token with all standard claims
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        
        # Check required fields
        if not payload.get("sub") or not payload.get("jti"):
            raise credentials_exception
            
        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Access token required.",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
            
        # Check if token is blacklisted
        if verify_token_blacklist(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
            
        # Get user from database
        user_identifier = payload.get("sub")
        user = db.query(User).filter(
            (User.email == user_identifier) | (User.username == user_identifier)
        ).first()
        
        if not user:
            raise credentials_exception
            
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
            
        # Check 2FA if required
        if require_2fa and user.is_2fa_enabled and not payload.get("2fa_verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="2FA verification required",
                headers={"X-2FA-Required": "true"},
            )
            
        # Update last activity time
        user.last_activity = datetime.utcnow()
        db.commit()
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"token_expired\""},
        )
    except jwt.JWTError:
        raise credentials_exception
    except Exception as e:
        print(f"Error authenticating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during authentication",
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Получить текущего активного пользователя.
    
    Это обертка над get_current_user, которая гарантирует, что пользователь активен.
    
    Args:
        current_user: Текущий аутентифицированный пользователь из get_current_user
        
    Returns:
        User: Аутентифицированный и активный пользователь
        
    Raises:
        HTTPException: Если пользователь неактивен (HTTP 403)
    """
    # Ensure current_user is resolved if it's a coroutine
    if asyncio.iscoroutine(current_user):
        current_user = await current_user
        
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись пользователя неактивна"
        )
        
    # Дополнительная проверка на блокировку аккаунта
    if current_user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись заблокирована. Пожалуйста, обратитесь в службу поддержки."
        )
        
    # Проверяем, не истек ли срок действия пароля
    if hasattr(current_user, 'password_expires_at') and current_user.password_expires_at:
        if current_user.password_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Срок действия пароля истек. Необходимо изменить пароль.",
                headers={"X-Password-Expired": "true"}
            )
    
    return current_user

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """
    Получить текущего пользователя, если аутентифицирован, в противном случае вернуть None.
    
    Полезно для эндпоинтов, которые должны работать как для аутентифицированных, 
    так и для неаутентифицированных пользователей. Менее строгая версия get_current_user, 
    которая не вызывает исключений для большинства проблем с аутентификацией.
    
    Args:
        request: Объект запроса FastAPI (для rate limiting)
        db: Сессия базы данных
        token: Опциональный JWT токен из заголовка Authorization
        
    Returns:
        Optional[User]: Аутентифицированный пользователь, если токен действителен, иначе None
    """
    if not token:
        return None
        
    try:
        # Используем стандартный get_current_user, но с require_2fa=False,
        # чтобы избежать проверки 2FA для необязательной аутентификации
        return await get_current_user(
            request=request,
            require_2fa=False,  # Не требовать 2FA для необязательной аутентификации
            db=db,
            token=token
        )
    except HTTPException as e:
        # Логируем только критические ошибки, игнорируя стандартные ошибки аутентификации
        if e.status_code >= 500:
            print(f"Ошибка при необязательной аутентификации: {str(e)}")
        return None
    except Exception as e:
        # Логируем неожиданные ошибки
        print(f"Неожиданная ошибка при необязательной аутентификации: {str(e)}")
        return None
    
    # Increment rate limit counter
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:optional:{client_ip}"
    with redis_client.pipeline() as pipe:
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, 60)
        pipe.execute()
    
    # Check if token is blacklisted
    if verify_token_blacklist(token):
        return None
    
    try:
        # First, try to get the user without requiring 2FA
        return await get_current_user(request, require_2fa=False, db=db, token=token)
    except HTTPException as e:
        # If 2FA is required, we still want to return the user
        # but with limited access (can only access 2FA endpoints)
        if e.status_code == status.HTTP_403_FORBIDDEN and "X-2FA-Required" in e.headers:
            try:
                # Decode token to get user info
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                    options={
                        "verify_aud": False,
                        "verify_iss": True,
                        "verify_sub": True,
                        "verify_iat": True,
                        "verify_exp": True,
                        "verify_nbf": False,
                        "leeway": 30
                    },
                    issuer=settings.PROJECT_NAME
                )
                
                # Get user from database
                username = payload.get("sub")
                if username:
                    user = db.query(User).filter(
                        (User.email == username) | (User.username == username)
                    ).first()
                    
                    # Only return the user if they're active
                    if user and user.is_active:
                        return user
                        
            except JWTError:
                pass
                
        # For any other exception, return None
        return None

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Получить текущего активного суперпользователя.
    
    Этот dependency гарантирует, что текущий пользователь активен и имеет права суперпользователя.
    Используется для административных эндпоинтов, требующих повышенных привилегий.
    
    Args:
        current_user: Текущий аутентифицированный пользователь из get_current_user
        
    Returns:
        User: Аутентифицированный суперпользователь
        
    Raises:
        HTTPException: 
            - 403: Если пользователь не является суперпользователем
            - 403: Если учетная запись пользователя неактивна
            - 403: Если учетная запись заблокирована
    """
    # Проверяем, что пользователь активен
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись пользователя неактивна"
        )
        
    # Проверяем, что пользователь не заблокирован
    if hasattr(current_user, 'is_locked') and current_user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись заблокирована. Обратитесь к администратору."
        )
    
    # Проверяем права суперпользователя
    if not current_user.is_superuser:
        # Логируем попытку доступа без прав
        print(f"Попытка доступа к защищенному ресурсу суперпользователя: {current_user.email}")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для доступа к этому ресурсу"
        )
    
    # Проверяем 2FA для суперпользователя
    # (можно добавить дополнительную проверку 2FA для админ-панели)
    if hasattr(current_user, 'is_2fa_enabled') and current_user.is_2fa_enabled:
        # Здесь можно добавить дополнительную проверку 2FA для админ-панели
        # Например, требовать повторную аутентификацию для критических операций
        pass
    
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active superuser.
    
    This dependency ensures the current user is both active and has superuser privileges.
    It should be used for admin-only endpoints that require elevated permissions.
    
    Args:
        current_user: The current authenticated user from get_current_user
        
    Returns:
        User: The authenticated superuser
        
    Raises:
        HTTPException: 
            - 403: If the user is not a superuser
            - 403: If the user account is not active
    """
    # Check if user is active (redundant but explicit)
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated"
        )
        
    # Check superuser status
    if not current_user.is_superuser:
        # Log failed admin access attempt (in production, use proper logging)
        print(f"Unauthorized admin access attempt by user: {current_user.email}")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. Administrator access required.",
            headers={"WWW-Authenticate": "Bearer error=\"insufficient_scope\""}
        )
        
    return current_user

def has_required_roles(user: User, required_roles: list[str]) -> bool:
    """
    Check if user has any of the required roles.
    
    This function checks if the user has any of the specified roles or is a superuser.
    It's typically used for route protection and permission checks.
    
    Args:
        user: The user to check roles for. Can be None.
        required_roles: List of role names that are allowed. If empty, any authenticated user passes.
        
    Returns:
        bool: 
            - True if user is a superuser
            - True if required_roles is empty and user is authenticated
            - True if user has at least one of the required roles
            - False otherwise
            
    Examples:
        # Check if user is admin or moderator
        if not has_required_roles(user, ["admin", "moderator"]):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    """
    # If no roles required, any authenticated user passes
    if not required_roles:
        return True
        
    # If no user provided, fail closed
    if not user:
        return False
        
    # Superusers automatically have all permissions
    if user.is_superuser:
        return True
    
    # Get user's role names (handle case where roles might not be loaded)
    try:
        if hasattr(user, 'roles') and user.roles is not None:
            # Handle both direct attribute and relationship
            if callable(user.roles):
                user_roles = user.roles()
            else:
                user_roles = user.roles
                
            user_role_names = [role.name for role in user_roles if hasattr(role, 'name')]
            
            # Check if any of the user's roles match the required roles (case-insensitive)
            return any(
                role.lower() in (r.lower() for r in user_role_names)
                for role in required_roles
                if role  # Skip empty strings
            )
    except Exception as e:
        # Log the error in production (using print for example only)
        print(f"Error checking user roles: {str(e)}")
        
    # Default deny if we can't determine roles
    return False
