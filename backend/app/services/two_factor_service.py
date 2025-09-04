"""
Service for Two-Factor Authentication (2FA) operations.
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any, Union

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.user import User
from app.models.user_login_attempt import UserLoginAttempt
from app.models.device import UserDevice
from app.schemas.two_factor import generate_totp_uri, TwoFactorSetupResponse
from .push_notification_service import push_notification_service

logger = logging.getLogger(__name__)

class SuspiciousActivityDetector:
    """Detects and handles suspicious authentication attempts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.max_attempts = settings.TWO_FACTOR_MAX_ATTEMPTS or 5
        self.lockout_time = timedelta(minutes=settings.TWO_FACTOR_LOCKOUT_MINUTES or 15)
    
    async def record_attempt(self, user_id: int, ip_address: str, success: bool) -> None:
        """Record a login attempt."""
        attempt = UserLoginAttempt(
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            attempt_time=datetime.utcnow()
        )
        self.db.add(attempt)
        await self.db.commit()
    
    async def check_suspicious_activity(self, user_id: int, ip_address: str) -> Dict[str, Any]:
        """Check for suspicious activity and return status."""
        # Get recent failed attempts
        result = await self.db.execute(
            select(UserLoginAttempt)
            .where(
                UserLoginAttempt.user_id == user_id,
                UserLoginAttempt.success == False,
                UserLoginAttempt.attempt_time > datetime.utcnow() - timedelta(hours=24)
            )
            .order_by(UserLoginAttempt.attempt_time.desc())
        )
        
        failed_attempts = result.scalars().all()
        
        # Check if account is locked
        if failed_attempts and len(failed_attempts) >= self.max_attempts:
            last_attempt = failed_attempts[0].attempt_time
            if datetime.utcnow() - last_attempt < self.lockout_time:
                return {
                    "is_locked": True,
                    "unlock_time": last_attempt + self.lockout_time,
                    "remaining_attempts": 0
                }
        
        # Check for suspicious patterns (e.g., multiple IPs, rapid attempts)
        suspicious_ips = set()
        for attempt in failed_attempts[:10]:  # Check last 10 attempts
            if attempt.ip_address != ip_address:
                suspicious_ips.add(attempt.ip_address)
        
        return {
            "is_locked": False,
            "suspicious_ips": list(suspicious_ips),
            "remaining_attempts": max(0, self.max_attempts - len(failed_attempts))
        }

class TwoFactorService:
    """Service for handling 2FA operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_detector = SuspiciousActivityDetector(db)
        
    async def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    async def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for 2FA."""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    async def setup_2fa(self, user: User) -> TwoFactorSetupResponse:
        """
        Set up 2FA for a user.
        
        Args:
            user: User to set up 2FA for
            
        Returns:
            TwoFactorSetupResponse with QR code URL and backup codes
        """
        # Generate new secret and backup codes
        secret = await self.generate_secret()
        backup_codes = await self.generate_backup_codes()
        
        # Generate TOTP URI for QR code
        totp_uri = generate_totp_uri(
            email=user.email or str(user.telegram_id),
            secret=secret,
            issuer_name=settings.PROJECT_NAME
        )
        
        # Update user with new 2FA data
        user.totp_secret = secret
        user.backup_codes = backup_codes
        
        # Don't enable 2FA yet - user needs to verify first
        user.is_2fa_enabled = False
        
        await self.db.commit()
        
        return TwoFactorSetupResponse(
            qr_code_url=totp_uri,
            secret=secret,
            backup_codes=backup_codes
        )
    
    async def verify_2fa(
        self, 
        user: User, 
        code: str, 
        is_backup_code: bool = False,
        is_push_notification: bool = False,
        request_ip: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Verify a 2FA code, backup code or push notification.
        
        Args:
            user: User to verify
            code: 6-digit code, backup code or verification token
            is_backup_code: Whether the code is a backup code
            is_push_notification: Whether this is a push notification verification
            request_ip: IP address of the request (for logging)
            device_info: Information about the device making the request
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        if not user.two_factor_enabled and not is_backup_code and not is_push_notification:
            return False, "2FA is not enabled for this account"
            
        if is_backup_code:
            return await self._verify_backup_code(user, code)
            
        if is_push_notification:
            # Here you would verify the push notification token
            # This is a simplified example - in production, you'd verify the token
            # against a stored verification request
            return await self._verify_push_notification(user, code, request_ip, device_info)
            
        # Record the attempt for security monitoring
        if request_ip:
            await self.activity_detector.record_attempt(user.id, request_ip, success=False)
        
        # Check if 2FA is locked due to too many attempts
        if await self.is_2fa_locked(user.id, request_ip):
            return False, "Too many failed attempts. Please try again later."
        
        # Verify the TOTP code
        totp = pyotp.TOTP(user.two_factor_secret)
        is_valid = totp.verify(code, valid_window=1)
        
        if is_valid and request_ip:
            # Record successful attempt
            await self.activity_detector.record_attempt(user.id, request_ip, success=True)
            return True, "Verification successful"
            
        return False, "Invalid verification code"
    
    async def _verify_backup_code(self, user: User, code: str) -> bool:
        """Verify a backup code and mark it as used."""
        if not user.backup_codes:
            return False
            
        # Normalize code (remove spaces, make uppercase)
        code = code.strip().upper()
        
        # Check if code is valid and not used
        if code in user.backup_codes:
            # Remove the used backup code
            user.backup_codes.remove(code)
            await self.db.commit()
            return True
            
        return False
    
    async def enable_2fa(self, user: User) -> None:
        """Enable 2FA for a user."""
        user.is_2fa_enabled = True
        await self.db.commit()
    
    async def disable_2fa(self, user: User) -> None:
        """Disable 2FA for a user."""
        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        await self.db.commit()
    
    async def regenerate_backup_codes(self, user: User) -> List[str]:
        """Generate new backup codes for a user."""
        if not user.is_2fa_enabled:
            raise ValueError("2FA is not enabled for this user")
            
        backup_codes = await self.generate_backup_codes()
        user.backup_codes = backup_codes
        await self.db.commit()
        return backup_codes

# Create a function to get the service instance
async def get_two_factor_service(db: AsyncSession) -> TwoFactorService:
    """Get an instance of the TwoFactorService.
    
    Args:
        db: Database session
        
    Returns:
        TwoFactorService: Instance of TwoFactorService
    """
    return TwoFactorService(db)
