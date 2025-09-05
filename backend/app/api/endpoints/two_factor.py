"""
Two-Factor Authentication (2FA) endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks, Security
from sqlalchemy.orm import Session
from typing import Optional

from app.core.security import (
    get_current_user,
    setup_2fa_for_user,
    verify_2fa_code,
    enable_2fa_for_user,
    disable_2fa_for_user,
    regenerate_backup_codes,
    get_current_active_user
)
from app.models.user import User
from app.schemas.two_factor import (
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorEnableRequest,
    TwoFactorDisableRequest,
    TwoFactorBackupCodesResponse,
    TwoFactorStatusResponse
)
from app.db.session import get_db

router = APIRouter(prefix="", tags=["2FA"])

@router.post(
    "/setup",
    response_model=TwoFactorSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Настройка двухфакторной аутентификации",
    description="Генерирует секретный ключ и резервные коды для настройки 2FA",
    response_description="Данные для настройки 2FA (QR-код, секретный ключ, резервные коды)",
    responses={
        200: {"description": "2FA успешно настроена"},
        400: {"description": "2FA уже включена"},
        401: {"description": "Не авторизован"}
    }
)
async def setup_2fa(
    current_user: User = Security(get_current_active_user),
    db: Session = Depends(get_db),
) -> TwoFactorSetupResponse:
    """
    Настройка двухфакторной аутентификации.
    
    Генерирует секретный ключ и резервные коды для настройки 2FA.
    Возвращает данные, необходимые для настройки приложения аутентификатора.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA уже включена для этого аккаунта"
        )
    
    try:
        # Генерируем секретный ключ, QR-код и резервные коды
        setup_data = setup_2fa_for_user(db, current_user)
        return setup_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при настройке 2FA"
        )

@router.post(
    "/enable",
    status_code=status.HTTP_200_OK,
    summary="Активация двухфакторной аутентификации",
    description="Активирует 2FA после подтверждения кода из приложения аутентификатора",
    responses={
        200: {"description": "2FA успешно активирована"},
        400: {"description": "Неверный код подтверждения или 2FA уже активирована"},
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещен"}
    }
)
async def enable_2fa(
    enable_data: TwoFactorEnableRequest,
    current_user: User = Security(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Активация двухфакторной аутентификации.
    
    Пользователь должен предоставить корректный код из приложения аутентификатора,
    чтобы подтвердить настройку 2FA.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA уже включена для этого аккаунта"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала настройте 2FA, отправив запрос на /2fa/setup"
        )
    
    try:
        # Проверяем код подтверждения и активируем 2FA
        if not enable_2fa_for_user(db, current_user, enable_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код подтверждения"
            )
        
        return {"status": "success", "message": "2FA успешно активирована"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при активации 2FA"
        )

@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Проверка кода подтверждения 2FA",
    description="Проверяет код подтверждения из приложения аутентификатора",
    responses={
        200: {"description": "Код подтверждения верен"},
        400: {"description": "Неверный код подтверждения"},
        401: {"description": "Не авторизован"}
    }
)
async def verify_2fa(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Security(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Проверка кода подтверждения 2FA.
    
    Используется для проверки кода из приложения аутентификатора.
    """
    if not current_user.is_2fa_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA не включена для этого аккаунта"
        )
    
    try:
        if not verify_2fa_code(db, current_user, verify_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код подтверждения"
            )
        
        return {"status": "success", "message": "Код подтверждения верен"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при проверке кода подтверждения"
        )

@router.post(
    "/disable",
    status_code=status.HTTP_200_OK,
    summary="Отключение двухфакторной аутентификации",
    description="Отключает 2FA для текущего пользователя",
    responses={
        200: {"description": "2FA успешно отключена"},
        400: {"description": "2FA не включена"},
        401: {"description": "Не авторизован"}
    }
)
async def disable_2fa(
    disable_data: TwoFactorDisableRequest,
    current_user: User = Security(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Отключение двухфакторной аутентификации.
    
    Требует подтверждения кода из приложения аутентификатора.
    """
    if not current_user.is_2fa_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA не включена для этого аккаунта"
        )
    
    try:
        # Проверяем код подтверждения
        if not verify_2fa_code(db, current_user, disable_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код подтверждения"
            )
        
        # Отключаем 2FA
        disable_2fa_for_user(db, current_user)
        
        return {"status": "success", "message": "2FA успешно отключена"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отключении 2FA"
        )

@router.post(
    "/regenerate-backup-codes",
    response_model=TwoFactorBackupCodesResponse,
    status_code=status.HTTP_200_OK,
    summary="Генерация новых резервных кодов",
    description="Генерирует новые резервные коды для 2FA",
    responses={
        200: {"description": "Новые резервные коды сгенерированы"},
        400: {"description": "2FA не включена"},
        401: {"description": "Не авторизован"}
    }
)
async def regenerate_backup_codes(
    current_user: User = Security(get_current_active_user),
    db: Session = Depends(get_db),
) -> TwoFactorBackupCodesResponse:
    """
    Генерация новых резервных кодов для 2FA.
    
    Старые резервные коды становятся недействительными.
    """
    if not current_user.is_2fa_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA не включена для этого аккаунта"
        )
    
    try:
        # Генерируем новые резервные коды
        backup_codes = regenerate_backup_codes(db, current_user)
        return TwoFactorBackupCodesResponse(backup_codes=backup_codes)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при генерации резервных кодов"
        )

@router.get(
    "/status",
    response_model=TwoFactorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Получение статуса 2FA",
    description="Возвращает текущий статус двухфакторной аутентификации",
    responses={
        200: {"description": "Статус 2FA получен"},
        401: {"description": "Не авторизован"}
    }
)
async def get_2fa_status(
    current_user: User = Security(get_current_active_user),
) -> TwoFactorStatusResponse:
    """
    Получение текущего статуса двухфакторной аутентификации.
    
    Возвращает информацию о том, включена ли 2FA, и количество оставшихся
    резервных кодов.
    """
    return TwoFactorStatusResponse(
        is_2fa_enabled=current_user.is_2fa_enabled,
        backup_codes_remaining=len(current_user.backup_codes) if current_user.backup_codes else 0,
        is_initial_setup=not current_user.totp_secret
    )
