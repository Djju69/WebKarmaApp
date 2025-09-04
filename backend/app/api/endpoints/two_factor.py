"""
Two-Factor Authentication (2FA) endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.two_factor import (
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorEnableRequest,
    TwoFactorDisableRequest,
    TwoFactorBackupCodesResponse,
    TwoFactorStatusResponse
)
from app.core.security.two_factor import (
    setup_2fa_for_user,
    verify_2fa_code,
    enable_2fa_for_user,
    disable_2fa_for_user,
    regenerate_backup_codes as regen_backup_codes
)
from app.core.database import get_db

router = APIRouter(prefix="/2fa", tags=["2FA"])

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
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    
    # Активируем 2FA
    current_user.is_2fa_enabled = True
    db.commit()

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Проверка кода подтверждения 2FA.
    
    # Отправляем уведомление об успешной активации
    background_tasks.add_task(
        send_2fa_enabled_email,
        email_to=current_user.email,
        username=current_user.username,
        ip_address=client_ip
    )
    
    return {"message": "Двухфакторная аутентификация успешно активирована"}

@router.post(
    "/disable",
    status_code=status.HTTP_200_OK,
    summary="Отключение двухфакторной аутентификации",
    description="Отключает 2FA для текущего пользователя",
    responses={
        200: {"description": "2FA успешно отключена"},
        400: {"description": "Неверный пароль или 2FA не активирована"},
        401: {"description": "Не авторизован"},
        403: {"description": "Требуется подтверждение 2FA"}
    }
)
async def disable_2fa(
    background_tasks: BackgroundTasks,
    request: Request,
    disable_request: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    two_factor_service: TwoFactorService = Depends(get_two_factor_service)
):
    """
    Отключение двухфакторной аутентификации.
    
    Требует подтверждения пароля пользователя и, если 2FA активна, кода подтверждения.
    """
    if not current_user.is_2fa_enabled and not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Двухфакторная аутентификация не настроена"
        )
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Проверяем пароль пользователя
    if not verify_password(disable_request.password, current_user.hashed_password):
        # Логируем попытку неверного ввода пароля
        logger.warning(
            "Failed 2FA disable attempt (wrong password) for user %s from IP %s",
            current_user.id,
            client_ip
        )
        
        # Отправляем уведомление о подозрительной активности
        background_tasks.add_task(
            send_suspicious_activity_alert,
            email_to=current_user.email,
            username=current_user.username,
            activity_type="failed_2fa_disable_password",
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent", "")
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль"
        )
    
    # Если 2FA активна, проверяем код подтверждения
    if current_user.is_2fa_enabled:
        if not disable_request.code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Требуется код подтверждения 2FA"
            )
            
        is_valid, message = await two_factor_service.verify_2fa(
            user=current_user,
            code=disable_request.code,
            request_ip=client_ip
        )
        
        if not is_valid:
            # Логируем попытку неверного ввода кода
            logger.warning(
                "Failed 2FA disable attempt (wrong code) for user %s from IP %s",
                current_user.id,
                client_ip
            )
            
            # Отправляем уведомление о подозрительной активности
            background_tasks.add_task(
                send_suspicious_activity_alert,
                email_to=current_user.email,
                username=current_user.username,
                activity_type="failed_2fa_disable_code",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent", "")
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message or "Неверный код подтверждения"
            )
    
    # Отключаем 2FA и очищаем данные
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = []
    
    db.commit()
    
    # Отправляем уведомление об отключении
    background_tasks.add_task(
        send_2fa_disabled_email,
        email_to=current_user.email,
        username=current_user.username,
        ip_address=client_ip
    )
    
    return {"message": "Двухфакторная аутентификация успешно отключена"}

@router.get(
    "/status",
    response_model=TwoFactorStatusResponse,
    summary="Получение статуса 2FA",
    description="Возвращает текущий статус двухфакторной аутентификации пользователя",
    response_description="Статус 2FA и количество оставшихся резервных кодов",
    responses={
        200: {"description": "Успешное получение статуса 2FA"},
        401: {"description": "Не авторизован"}
    }
)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    two_factor_service: TwoFactorService = Depends(get_two_factor_service)
) -> TwoFactorStatusResponse:
    """
    Получение текущего статуса двухфакторной аутентификации.
    
    Возвращает информацию о том, включена ли 2FA, а также количество
    оставшихся резервных кодов.
    """
    # Проверяем, настроена ли 2FA (есть ли сохраненный секретный ключ)
    is_2fa_setup = current_user.totp_secret is not None
    
    # Получаем количество оставшихся резервных кодов
    backup_codes_remaining = len(current_user.backup_codes or [])
    
    # Проверяем, активна ли 2FA (настроена и включена)
    is_2fa_active = current_user.is_2fa_enabled and is_2fa_setup
    
    # Получаем дату последнего изменения настроек 2FA (если доступно)
    last_2fa_change = getattr(current_user, 'two_factor_last_changed', None)
    
    return TwoFactorStatusResponse(
        is_2fa_enabled=is_2fa_active,
        is_2fa_setup=is_2fa_setup,
        backup_codes_remaining=backup_codes_remaining,
        last_2fa_change=last_2fa_change
    )

@router.post(
    "/regenerate-backup-codes",
    response_model=TwoFactorBackupCodesResponse,
    status_code=status.HTTP_200_OK,
    summary="Генерация новых резервных кодов",
    description="Генерирует новые резервные коды для двухфакторной аутентификации",
    response_description="Список новых резервных кодов",
    responses={
        200: {"description": "Успешная генерация резервных кодов"},
        400: {"description": "2FA не включена или не настроена"},
        401: {"description": "Не авторизован"},
        403: {"description": "Требуется подтверждение 2FA"}
    }
)
async def regenerate_backup_codes(
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    two_factor_service: TwoFactorService = Depends(get_two_factor_service)
) -> TwoFactorBackupCodesResponse:
    """
    Генерация новых резервных кодов для двухфакторной аутентификации.
    
    Генерирует новый набор резервных кодов, которые можно использовать
    для входа в случае утери доступа к приложению аутентификатора.
    
    ВАЖНО: При генерации новых кодов все предыдущие резервные коды становятся недействительными.
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала настройте двухфакторную аутентификацию"
        )
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Если 2FA включена, требуем подтверждение с помощью кода
    if current_user.is_2fa_enabled:
        # В этом эндпоинте мы ожидаем код подтверждения в заголовке X-2FA-Code
        code = request.headers.get("X-2FA-Code")
        if not code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Требуется подтверждение 2FA. Укажите код в заголовке X-2FA-Code."
            )
            
        # Проверяем код подтверждения
        is_valid, message = await two_factor_service.verify_2fa(
            user=current_user,
            code=code,
            request_ip=client_ip
        )
        
        if not is_valid:
            # Логируем попытку неверного ввода кода
            logger.warning(
                "Failed backup codes regeneration attempt (wrong code) for user %s from IP %s",
                current_user.id,
                client_ip
            )
            
            # Отправляем уведомление о подозрительной активности
            background_tasks.add_task(
                send_suspicious_activity_alert,
                email_to=current_user.email,
                username=current_user.username,
                activity_type="failed_backup_codes_regeneration",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent", "")
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message or "Неверный код подтверждения"
            )
    
    # Генерируем новые резервные коды
    backup_codes = await two_factor_service.regenerate_backup_codes(current_user)
    
    # Сохраняем изменения в базе данных
    db.commit()
    
    # Отправляем уведомление о генерации новых резервных кодов
    background_tasks.add_task(
        send_2fa_backup_codes_email,
        email_to=current_user.email,
        username=current_user.username,
        ip_address=client_ip,
        backup_codes=backup_codes
    )
    
    return TwoFactorBackupCodesResponse(backup_codes=backup_codes)
