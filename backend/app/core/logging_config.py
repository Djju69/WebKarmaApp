"""
Настройка логирования для приложения.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings


def setup_logging() -> None:
    """Настройка логирования для приложения."""
    # Создаем директорию для логов, если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Базовый формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Уровень логирования из настроек
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Базовый конфиг для корневого логгера
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/application.log", encoding="utf-8")
        ]
    )
    
    # Настройка логгера для Telegram
    telegram_logger = logging.getLogger("telegram")
    telegram_logger.setLevel(logging.WARNING)  # Уменьшаем уровень логирования для библиотеки
    
    # Логгер для нашего приложения
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    # Файловый обработчик для ошибок
    error_handler = logging.FileHandler("logs/error.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    
    # Добавляем обработчик ошибок
    app_logger.addHandler(error_handler)
    
    # Настраиваем Sentry для мониторинга ошибок
    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Уровень логирования для Sentry
            event_level=logging.ERROR  # Уровень событий, которые отправляются в Sentry
        )
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,
            environment=settings.ENVIRONMENT,
            release=settings.VERSION
        )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Получить логгер с указанным именем."""
    return logging.getLogger(f"app.{name}" if name else "app")
