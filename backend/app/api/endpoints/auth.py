"""
Authentication endpoints for user registration, login, token refresh, etc.
"""
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    Body,
    Request,
    BackgroundTasks,
    Response
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    create_verification_token,
    verify_verification_token,
    verify_token_blacklist,
    add_token_to_blacklist,
    get_current_user,
    get_current_active_user,
    get_current_active_superuser,
)
from app.core.config import settings
from app.db.base import get_db
from app.models.user import User, UserRole
from app.schemas.token import (
    Token, 
    TokenPayload, 
    UserRegister, 
    PasswordResetRequest, 
    PasswordResetConfirm,
    EmailVerification,
    TokenResponse
)
from app.schemas.user import User as UserSchema, UserInDB

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        429: {"description": "Too Many Requests"},
        500: {"description": "Internal Server Error"},
    },
)

def send_email(recipient: str, subject: str, body: str) -> None:
    """Send an email with the given subject and body."""
    if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.EMAIL_FROM]):
        # In development, just log the email instead of sending it
        print(f"[DEV] Email to {recipient} - {subject}:\n{body}")
        return
        
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send email: {e}")


def send_verification_email(email: str, token: str) -> None:
    """Send an email verification email."""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your email address"
    body = f"""
    <h2>Welcome to KarmaSystem!</h2>
    <p>Please click the link below to verify your email address:</p>
    <p><a href="{verification_url}">Verify Email</a></p>
    <p>If you didn't create an account, you can safely ignore this email.</p>
    """
    send_email(email, subject, body)


def send_password_reset_email(email: str, token: str) -> None:
    """Send a password reset email."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Password Reset Request"
    body = f"""
    <h2>Password Reset</h2>
    <p>You requested to reset your password. Click the link below to set a new password:</p>
    <p><a href="{reset_url}">Reset Password</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>If you didn't request a password reset, please ignore this email.</p>
    """
    send_email(email, subject, body)

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserSchema,
    summary="Register a new user",
    description="Create a new user account and send verification email",
    response_description="The created user",
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Username or email already registered"},
        422: {"description": "Validation error"}
    }
)
async def register(
    background_tasks: BackgroundTasks,
    user_in: UserRegister,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user account.
    
    - **email**: User's email address (must be unique)
    - **password**: Password (8-128 characters)
    - **username**: Username (3-50 characters, alphanumeric + _)
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    """
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.email == user_in.email) | (User.username == user_in.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user_in.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user_data = user_in.dict(exclude={"password"})
    user_data["hashed_password"] = hashed_password
    user_data["is_active"] = True
    user_data["is_verified"] = not settings.REQUIRE_EMAIL_VERIFICATION
    
    # Default to user role
    user = User(**user_data)
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user"
        ) from e
    
    # Send verification email if required
    if settings.REQUIRE_EMAIL_VERIFICATION:
        token = create_verification_token(user.email)
        background_tasks.add_task(send_verification_email, user.email, token)
    
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="OAuth2 Login",
    description="Authenticate user and get access token",
    response_description="Access token and token type",
    responses={
        200: {
            "description": "Successful login or 2FA verification required",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "string",
                        "refresh_token": "string",
                        "token_type": "bearer",
                        "requires_2fa": False,
                        "is_2fa_verified": True
                    }
                }
            }
        },
        400: {"description": "Incorrect username or password or invalid 2FA code"},
        401: {"description": "Invalid or expired token"},
        403: {"description": "Email not verified or 2FA verification required"},
        404: {"description": "User not found"},
        429: {"description": "Too many login attempts"}
    }
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    code: Optional[str] = Body(None, embed=True)  # 2FA код (опционально для первого шага)
):
    """
    Аутентификация пользователя и получение токенов доступа.
    
    Если у пользователя включена 2FA, первый запрос вернет токен, требующий верификации 2FA.
    Клиент должен запросить у пользователя код 2FA и отправить его в параметре `code`.
    
    Args:
        request: Объект запроса
        db: Сессия базы данных
        form_data: Данные формы аутентификации (username, password)
        code: Код двухфакторной аутентификации (опционально)
        
    Returns:
        TokenResponse: Токены доступа и информация о пользователе
        
    Raises:
        HTTPException: В случае ошибки аутентификации
    """
    # Находим пользователя по email или username
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()
    
    # Проверяем существование пользователя и корректность пароля
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Логируем неудачную попытку входа
        print(f"Неудачная попытка входа для пользователя: {form_data.username}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email/username или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем активность пользователя
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись неактивна"
        )
    
    # Если включена 2FA и код не предоставлен, возвращаем токен, требующий 2FA
    if user.is_2fa_enabled and not code:
        # Создаем токен с коротким сроком действия только для верификации 2FA
        access_token_expires = timedelta(minutes=5)
        access_token = create_access_token(
            data={"sub": user.email or user.username},
            expires_delta=access_token_expires,
            is_2fa_verified=False,  # Отмечаем, что 2FA не пройдена
            scope="2fa_required"    # Ограниченная область действия
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "requires_2fa": True,
            "message": "Требуется двухфакторная аутентификация"
        }
    
    # Если включена 2FA и предоставлен код, проверяем его
    if user.is_2fa_enabled and code:
        from app.services.two_factor_service import TwoFactorService
        
        try:
            two_factor_service = TwoFactorService(db)
            
            # Проверяем код 2FA
            is_valid = two_factor_service.verify_code(user.id, code)
            
            if not is_valid:
                # Логируем неудачную попытку ввода кода 2FA
                print(f"Неверный код 2FA для пользователя: {user.email or user.username}")
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Неверный код двухфакторной аутентификации",
                    headers={"WWW-Authenticate": "Bearer error=\"invalid_2fa\""},
                )
                
            # Логируем успешную 2FA аутентификацию
            print(f"Успешная 2FA аутентификация для пользователя: {user.email or user.username}")
            
        except Exception as e:
            print(f"Ошибка при верификации 2FA: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при проверке кода двухфакторной аутентификации"
            )
    
    # Генерируем токены доступа и обновления
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Получаем информацию о клиенте для привязки токена
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else "unknown"
    
    # Создаем access token с отметкой о прохождении 2FA
    access_token = create_access_token(
        data={"sub": user.email or user.username},
        expires_delta=access_token_expires,
        is_2fa_verified=user.is_2fa_enabled,  # Отмечаем, что 2FA пройдена (если включена)
        user_agent=user_agent,
        ip_address=client_host
    )
    
    # Создаем refresh token
    refresh_token = create_refresh_token(
        data={"sub": user.email or user.username},
        expires_delta=refresh_token_expires,
        user_agent=user_agent,
        ip_address=client_host
    )
    
    # Обновляем время последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Логируем успешный вход
    print(f"Успешный вход пользователя: {user.email or user.username}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "requires_2fa": False,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_2fa_enabled": user.is_2fa_enabled,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    }

@router.post(
    "/verify-2fa",
    response_model=TokenResponse,
    summary="Верификация 2FA кода",
    description="Верификация кода двухфакторной аутентификации после начального входа",
    response_description="Новые токены с подтвержденной 2FA",
    responses={
        200: {
            "description": "2FA успешно подтверждена",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "string",
                        "refresh_token": "string",
                        "token_type": "bearer",
                        "is_2fa_verified": True,
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "username": "user123",
                            "is_active": True,
                            "is_2fa_enabled": True
                        }
                    }
                }
            }
        },
        400: {"description": "Неверный или устаревший код 2FA"},
        401: {"description": "Неверный или устаревший токен"},
        403: {"description": "2FA не включена для этого пользователя"},
        404: {"description": "Пользователь не найден"}
    }
)
async def verify_2fa(
    request: Request,
    code: str = Body(..., embed=True, description="6-значный код из приложения аутентификатора"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Подтверждение кода двухфакторной аутентификации.
    
    Этот эндпоинт вызывается после успешного входа, если у пользователя включена 2FA.
    
    Args:
        request: Объект запроса
        code: 6-значный код из приложения аутентификатора
        current_user: Текущий аутентифицированный пользователь
        db: Сессия базы данных
        
    Returns:
        TokenResponse: Новые токены с подтвержденной 2FA и информация о пользователе
        
    Raises:
        HTTPException: В случае ошибки верификации
    """
    # Проверяем, включена ли 2FA для пользователя
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Двухфакторная аутентификация не включена для этого пользователя"
        )
    
    # Получаем сервис 2FA
    from app.services.two_factor_service import TwoFactorService
    
    try:
        two_factor_service = TwoFactorService(db)
        
        # Проверяем код 2FA
        is_valid = two_factor_service.verify_code(current_user.id, code)
        
        if not is_valid:
            # Логируем неудачную попытку верификации
            print(f"Неудачная попытка верификации 2FA для пользователя: {current_user.email or current_user.username}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный или устаревший код двухфакторной аутентификации"
            )
        
        # Генерируем новые токены с подтвержденной 2FA
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Получаем информацию о клиенте для привязки токена
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else "unknown"
        
        # Создаем новые токены с подтвержденной 2FA
        access_token = create_access_token(
            data={"sub": current_user.email or current_user.username},
            expires_delta=access_token_expires,
            is_2fa_verified=True,  # Подтверждаем прохождение 2FA
            user_agent=user_agent,
            ip_address=client_host
        )
        
        refresh_token = create_refresh_token(
            data={"sub": current_user.email or current_user.username},
            expires_delta=refresh_token_expires,
            user_agent=user_agent,
            ip_address=client_host
        )
        
        # Обновляем время последнего входа
        current_user.last_login = datetime.utcnow()
        db.commit()
        
        # Логируем успешную верификацию 2FA
        print(f"Успешная верификация 2FA для пользователя: {current_user.email or current_user.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "is_2fa_verified": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "is_active": current_user.is_active,
                "is_superuser": current_user.is_superuser,
                "is_2fa_enabled": current_user.is_2fa_enabled,
                "created_at": current_user.created_at,
                "last_login": current_user.last_login
            }
        }
        
    except Exception as e:
        # Логируем ошибку при верификации 2FA
        print(f"Ошибка при верификации 2FA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при верификации кода двухфакторной аутентификации"
        )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токена доступа",
    description="Обновление истекшего токена доступа с использованием refresh токена",
    response_description="Новый access token и refresh token",
    responses={
        200: {
            "description": "Токен успешно обновлен",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "string",
                        "refresh_token": "string",
                        "token_type": "bearer",
                        "requires_2fa": False,
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "username": "user123",
                            "is_active": True,
                            "is_2fa_enabled": False
                        }
                    }
                }
            }
        },
        400: {"description": "Неверный или устаревший refresh токен"},
        401: {"description": "Неверный или устаревший токен"},
        403: {"description": "Пользователь неактивен или недостаточно прав"},
        404: {"description": "Пользователь не найден"}
    }
)
async def refresh_token(
    request: Request,
    token_payload: TokenPayload,
    db: Session = Depends(get_db),
):
    """
    Обновление access token с использованием валидного refresh токена.
    
    Если у пользователя включена 2FA, новый access token будет требовать повторной верификации 2FA.
    
    Args:
        request: Объект запроса
        token_payload: Данные из refresh токена
        db: Сессия базы данных
        
    Returns:
        TokenResponse: Новые токены доступа и обновления
        
    Raises:
        HTTPException: В случае ошибки обновления токена
    """
    try:
        # Получаем пользователя из данных токена
        user_identifier = token_payload.sub
        user = db.query(User).filter(
            (User.email == user_identifier) | (User.username == user_identifier)
        ).first()
        
        # Проверяем существование и активность пользователя
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учетная запись неактивна"
            )
        
        # Генерируем новые токены
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Получаем информацию о клиенте для привязки токена
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else "unknown"
        
        # Создаем новый access token (потребует 2FA, если включена для пользователя)
        access_token = create_access_token(
            data={"sub": user_identifier},
            expires_delta=access_token_expires,
            is_2fa_verified=not user.is_2fa_enabled,  # Требуем 2FA, если она включена
            user_agent=user_agent,
            ip_address=client_host
        )
        
        # Создаем новый refresh token с поддержкой ротации
        refresh_token = create_refresh_token(
            data={"sub": user_identifier},
            expires_delta=refresh_token_expires,
            user_agent=user_agent,
            ip_address=client_host,
            rotation_enabled=True  # Включаем ротацию токенов
        )
        
        # Логируем успешное обновление токена
        print(f"Токен обновлен для пользователя: {user.email or user.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "requires_2fa": user.is_2fa_enabled,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "is_2fa_enabled": user.is_2fa_enabled,
                "created_at": user.created_at,
                "last_login": user.last_login
            }
        }
        
    except HTTPException:
        # Пробрасываем известные исключения дальше
        raise
        
    except Exception as e:
        # Логируем неизвестные ошибки
        print(f"Ошибка при обновлении токена: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении токена"
        )

@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verify email address",
    description="Verify user's email address using verification token",
    responses={
        200: {"description": "Email verified successfully"},
        400: {"description": "Invalid or expired token"}
    }
)
async def verify_email(
    token_data: EmailVerification,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify user's email address using the verification token.
    """
    email = verify_verification_token(token_data.token, "verify")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    user.is_verified = True
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend verification email",
    description="Resend email verification link",
    responses={
        200: {"description": "Verification email sent"},
        400: {"description": "Email already verified"},
        404: {"description": "User not found"}
    }
)
async def resend_verification(
    background_tasks: BackgroundTasks,
    email_data: Dict[str, str],
    db: Session = Depends(get_db)
) -> Any:
    """
    Resend email verification link.
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    token = create_verification_token(user.email)
    background_tasks.add_task(send_verification_email, user.email, token)
    
    return {"message": "Verification email sent"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Send password reset email",
    responses={
        200: {"description": "Password reset email sent"},
        404: {"description": "User not found"}
    }
)
async def forgot_password(
    background_tasks: BackgroundTasks,
    email_data: Dict[str, str],
    db: Session = Depends(get_db)
) -> Any:
    """
    Send password reset email.
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = create_verification_token(user.email, "reset")
        background_tasks.add_task(send_password_reset_email, user.email, token)
    
    # Always return success to prevent email enumeration
    return {"message": "If your email exists in our system, you will receive a password reset link"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password",
    description="Reset user password using reset token",
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid or expired token"},
        404: {"description": "User not found"}
    }
)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset user password using the reset token.
    """
    email = verify_verification_token(reset_data.token, "reset")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    db.commit()
    
    return {"message": "Password reset successful"}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Revoke the current access and refresh tokens",
    responses={
        200: {"description": "Successfully logged out"}
    }
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Logout user by revoking the current access and refresh tokens.
    """
    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        scheme, token = auth_header.split()
        if scheme.lower() == "bearer":
            # Add token to blacklist with remaining time until expiration
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                    options={"verify_exp": False}
                )
                exp = payload.get("exp")
                if exp:
                    # Calculate remaining time until token expiration
                    remaining_time = int(exp - time.time())
                    if remaining_time > 0:
                        add_token_to_blacklist(token, remaining_time)
            except JWTError:
                pass
    
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Get current user",
    description="Get the current authenticated user's profile",
    responses={
        200: {"description": "User profile"},
        401: {"description": "Not authenticated"}
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user's profile.
    """
    return current_user
