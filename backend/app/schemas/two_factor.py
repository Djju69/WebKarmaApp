"""
Schemas for Two-Factor Authentication (2FA) operations.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator, HttpUrl
import pyotp

class TwoFactorSetupResponse(BaseModel):
    """Response model for 2FA setup."""
    qr_code: str = Field(..., description="Base64 encoded QR code image to scan with authenticator app")
    secret: str = Field(..., description="Secret key for manual entry")
    backup_codes: List[str] = Field(..., description="List of backup codes")
    is_enabled: bool = Field(..., description="Whether 2FA is already enabled")

class TwoFactorVerifyRequest(BaseModel):
    """Request model for 2FA verification."""
    code: str = Field(..., min_length=6, max_length=10, 
                     description="6-digit verification code from authenticator app or a backup code")
    
    @validator('code')
    def validate_code_format(cls, v):
        # For backup codes, we allow letters and dashes
        if not (v.replace('-', '').isalnum() and 6 <= len(v) <= 10):
            raise ValueError("Invalid verification code format")
        return v

class TwoFactorEnableRequest(TwoFactorVerifyRequest):
    """Request model for enabling 2FA."""
    pass

class TwoFactorDisableRequest(BaseModel):
    """Request model for disabling 2FA."""
    code: str = Field(..., min_length=6, max_length=10,
                     description="6-digit verification code from authenticator app or a backup code")

class TwoFactorBackupCodesResponse(BaseModel):
    """Response model for 2FA backup codes."""
    backup_codes: List[str] = Field(..., description="List of new backup codes")

class TwoFactorStatusResponse(BaseModel):
    """Response model for 2FA status."""
    is_2fa_enabled: bool = Field(..., description="Whether 2FA is enabled for the account")
    backup_codes_remaining: int = Field(..., description="Number of unused backup codes remaining")
    is_initial_setup: bool = Field(..., description="Whether 2FA is not yet set up")

# Helper function to generate TOTP URI
def generate_totp_uri(email: str, secret: str, issuer_name: str = "WebKarmaApp") -> str:
    """
    Generate a TOTP URI for QR code generation.
    
    Args:
        email: User's email or ID
        secret: TOTP secret key
        issuer_name: Name of the service (default: "WebKarmaApp")
        
    Returns:
        str: TOTP URI string
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer_name
    )
