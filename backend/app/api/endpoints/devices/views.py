"""
API endpoints for managing user devices for 2FA push notifications.
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.device import UserDevice
from app.schemas.device import (
    DeviceCreate, 
    DeviceResponse, 
    DeviceUpdate,
    DeviceVerificationRequest,
    DeviceVerificationResponse
)
from app.core.security import get_current_user
from app.services.two_factor_service import TwoFactorService, get_two_factor_service

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


@router.post("/devices/", 
            response_model=DeviceResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Register a new device",
            description="Register a new device for the current user to receive 2FA push notifications.")
async def register_device(
    device_data: DeviceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new device for the current user.
    
    This endpoint allows users to register a new device for receiving 2FA push notifications.
    """
    # Check if device with this ID already exists for the user
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.user_id == current_user.id)
        .where(UserDevice.device_id == device_data.device_id)
    )
    existing_device = result.scalars().first()
    
    if existing_device:
        # Update existing device
        existing_device.push_token = device_data.push_token
        existing_device.device_name = device_data.device_name
        existing_device.os = device_data.os
        existing_device.os_version = device_data.os_version
        existing_device.browser = device_data.browser
        existing_device.browser_version = device_data.browser_version
        existing_device.last_ip_address = request.client.host
        existing_device.last_used_at = datetime.utcnow()
        existing_device.is_active = True
        
        await db.commit()
        await db.refresh(existing_device)
        
        return existing_device
    else:
        # Create new device
        device = UserDevice(
            user_id=current_user.id,
            device_id=device_data.device_id,
            push_token=device_data.push_token,
            device_name=device_data.device_name,
            os=device_data.os,
            os_version=device_data.os_version,
            browser=device_data.browser,
            browser_version=device_data.browser_version,
            last_ip_address=request.client.host,
            is_active=True,
            is_trusted=False  # New devices are not trusted by default
        )
        
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        return device


@router.get("/devices/", 
           response_model=List[DeviceResponse],
           summary="List user devices",
           description="Get a list of all devices registered for the current user.")
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of all devices registered for the current user.
    """
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.user_id == current_user.id)
        .order_by(UserDevice.last_used_at.desc())
    )
    return result.scalars().all()


@router.get("/devices/{device_id}", 
           response_model=DeviceResponse,
           summary="Get device details",
           responses={
               404: {"description": "Device not found"}
           })
async def get_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific device.
    """
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.id == device_id)
        .where(UserDevice.user_id == current_user.id)
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
        
    return device


@router.put("/devices/{device_id}", 
           response_model=DeviceResponse,
           summary="Update device",
           responses={
               404: {"description": "Device not found"}
           })
async def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update device information.
    """
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.id == device_id)
        .where(UserDevice.user_id == current_user.id)
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Update fields if they are provided
    if device_update.device_name is not None:
        device.device_name = device_update.device_name
    if device_update.is_trusted is not None:
        device.is_trusted = device_update.is_trusted
    if device_update.push_token is not None:
        device.push_token = device_update.push_token
    
    device.last_used_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(device)
    
    return device


@router.delete("/devices/{device_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete device",
            description="Delete a device",
            response_model=None,
            responses={
                204: {"description": "Device deleted successfully"},
                404: {"description": "Device not found"}
            })
async def delete_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a device.
    """
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.id == device_id)
        .where(UserDevice.user_id == current_user.id)
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    await db.delete(device)
    await db.commit()
    
    return None


async def get_2fa_service(
    db: AsyncSession = Depends(get_db)
) -> TwoFactorService:
    """Dependency that provides a TwoFactorService instance."""
    return await get_two_factor_service(db)

@router.post("/devices/{device_id}/verify",
            response_model=DeviceVerificationResponse,
            summary="Verify device",
            description="Verify a device using 2FA code or push notification",
            responses={
                200: {"model": DeviceVerificationResponse, "description": "Device verified successfully"},
                400: {"description": "Invalid verification code or token"},
                404: {"description": "Device not found"}
            })
async def verify_device(
    device_id: str,
    verification_data: DeviceVerificationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    two_factor_service: TwoFactorService = Depends(get_2fa_service)
) -> DeviceVerificationResponse:
    """
    Verify a device using 2FA code or push notification.
    """
    # Get the device
    result = await db.execute(
        select(UserDevice)
        .where(UserDevice.id == device_id)
        .where(UserDevice.user_id == current_user.id)
    )
    device = result.scalars().first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Verify the 2FA code or push notification
    if verification_data.verification_type == "code":
        # Verify TOTP code
        is_valid, message = await two_factor_service.verify_2fa(
            user=current_user,
            code=verification_data.code,
            request_ip=request.client.host
        )
    elif verification_data.verification_type == "push":
        # Verify push notification response
        is_valid, message = await two_factor_service.verify_2fa(
            user=current_user,
            code=verification_data.code,
            is_push_notification=True,
            request_ip=request.client.host,
            device_info={
                "device_id": device.device_id,
                "device_name": device.device_name,
                "os": device.os,
                "browser": device.browser
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification type. Must be 'code' or 'push'"
        )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message or "Invalid verification code or token"
        )
    
    # Mark device as trusted
    device.is_trusted = True
    device.last_used_at = datetime.utcnow()
    await db.commit()
    
    return {
        "success": True,
        "message": "Device verified and trusted",
        "device_id": str(device.id)
    }
