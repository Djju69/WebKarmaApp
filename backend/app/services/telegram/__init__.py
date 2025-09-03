"""
Telegram API service module.
Handles all interactions with Telegram Bot API.
"""

from .client import TelegramClient
from .webhook import setup_webhook, verify_telegram_webhook
from .handlers import register_handlers
from .bot import create_application, get_application
from .error_handling import TelegramErrorHandler, error_handler, setup_error_handlers

__all__ = [
    'TelegramClient',
    'setup_webhook',
    'verify_telegram_webhook',
    'register_handlers',
    'create_application',
    'get_application',
    'TelegramErrorHandler',
    'error_handler',
    'setup_error_handlers'
]
