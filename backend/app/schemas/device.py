"""
Pydantic schemas for device management and 2FA push notifications.
"""
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum


class DeviceVerificationType(str, Enum):
    CODE = "code"
    PUSH = "push"


class DeviceBase(BaseModel):
    """Base schema for device information."""
    device_id: str = Field(..., description="Unique identifier for the device")
    device_name: Optional[str] = Field(None, description="User-friendly name for the device")
    os: Optional[str] = Field(None, description="Operating system of the device")
    os_version: Optional[str] = Field(None, description="Version of the operating system")
    browser: Optional[str] = Field(None, description="Browser used on the device")
    browser_version: Optional[str] = Field(None, description="Version of the browser")
    is_active: bool = Field(True, description="Whether the device is active")
    is_trusted: bool = Field(False, description="Whether the device is trusted")


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""
    push_token: Optional[str] = Field(
        None, 
        description="Push notification token for the device (FCM/APNS)"
    )


class DeviceUpdate(BaseModel):
    """Schema for updating device information."""
    device_name: Optional[str] = Field(None, description="User-friendly name for the device")
    is_trusted: Optional[bool] = Field(None, description="Whether the device is trusted")
    push_token: Optional[str] = Field(
        None, 
        description="Push notification token for the device (FCM/APNS)"
    )


class DeviceResponse(DeviceBase):
    """Schema for device response."""
    id: int = Field(..., description="Unique identifier for the device record")
    user_id: int = Field(..., description="ID of the user who owns the device")
    last_ip_address: Optional[str] = Field(None, description="Last known IP address of the device")
    created_at: datetime = Field(..., description="When the device was registered")
    last_used_at: datetime = Field(..., description="When the device was last used")

    class Config:
        orm_mode = True


class DeviceVerificationRequest(BaseModel):
    """Schema for device verification request."""
    verification_type: Literal["code", "push"] = Field(
        ..., 
        description="Type of verification: 'code' for TOTP code, 'push' for push notification"
    )
    code: str = Field(
        ..., 
        description="Verification code from authenticator app or push notification"
    )
    device_id: Optional[str] = Field(
        None,
        description="ID of the device being verified (required for push verification)"
    )

    @validator('device_id')
    def device_id_required_for_push(cls, v, values):
        if values.get('verification_type') == 'push' and not v:
            raise ValueError("device_id is required for push verification")
        return v


class DeviceVerificationResponse(BaseModel):
    """Schema for device verification response."""
    success: bool = Field(..., description="Whether the verification was successful")
    message: str = Field(..., description="Verification result message")
    device_id: str = Field(..., description="ID of the verified device")


class PushNotificationRequest(BaseModel):
    """Schema for sending push notifications."""
    title: str = Field(..., description="Title of the push notification")
    message: str = Field(..., description="Message content of the push notification")
    data: Optional[dict] = Field(
        None,
        description="Additional data to include with the notification"
    )
    image: Optional[HttpUrl] = Field(
        None,
        description="URL of an image to include in the notification"
    )


class PushNotificationResponse(BaseModel):
    """Schema for push notification response."""
    success: bool = Field(..., description="Whether the notification was sent successfully")
    message_id: Optional[str] = Field(None, description="ID of the sent message")
    error: Optional[str] = Field(None, description="Error message if sending failed")


class DeviceListResponse(BaseModel):
    """Schema for listing user devices."""
    devices: List[DeviceResponse] = Field(..., description="List of user devices")
    total: int = Field(..., description="Total number of devices")


class TrustedDeviceCreate(BaseModel):
    """Schema for creating a trusted device."""
    device_id: str = Field(..., description="Unique identifier for the device")
    device_name: str = Field(..., description="User-friendly name for the device")
    public_key: str = Field(..., description="Public key for device authentication")
