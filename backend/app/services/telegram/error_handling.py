"""
Обработка ошибок для Telegram бота.
"""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar, Optional

from telegram import Update, Bot
from telegram.error import (
    TelegramError, 
    NetworkError, 
    RetryAfter,
    TimedOut,
    BadRequest,
    Conflict,
    Unauthorized
)

from app.core.config import settings

logger = logging.getLogger("app.telegram.errors")

T = TypeVar('T')

class TelegramErrorHandler:
    """Класс для обработки ошибок Telegram API."""
    
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
    
    async def _send_error_notification(self, error: Exception, update: Optional[Update] = None) -> None:
        """Отправить уведомление об ошибке администраторам."""
        if not self.bot or not settings.TELEGRAM_ADMIN_IDS:
            return
            
        error_message = f"❌ *Ошибка в боте*\n\n"
        
        if update and update.effective_chat:
            error_message += f"Чат: {update.effective_chat.title or 'ЛС'}\n"
            if update.effective_user:
                error_message += f"Пользователь: {update.effective_user.mention_markdown_v2()}\n"
        
        error_message += f"\n*Ошибка:*\n```\n{str(error)}\n```"
        
        if hasattr(error, '__traceback__'):
            import traceback
            error_message += f"\n\n*Трейсбек:*\n```\n{''.join(traceback.format_tb(error.__traceback__))}\n```"
        
        for admin_id in settings.TELEGRAM_ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=error_message,
                    parse_mode='MarkdownV2',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление об ошибке администратору {admin_id}: {e}")
    
    async def handle_error(self, update: object, context) -> None:
        """Обработчик ошибок для telegram.ext.Application."""
        error = context.error
        
        if isinstance(error, RetryAfter):
            # Обработка ограничения частоты запросов
            wait_time = error.retry_after
            logger.warning(f"Превышен лимит запросов. Ожидание {wait_time} секунд...")
            await asyncio.sleep(wait_time)
            return
            
        if isinstance(error, (NetworkError, TimedOut)):
            # Обработка сетевых ошибок
            logger.error(f"Сетевая ошибка: {error}")
            return
            
        if isinstance(error, BadRequest):
            # Некорректный запрос к API Telegram
            logger.error(f"Некорректный запрос: {error}")
            return
            
        if isinstance(error, Unauthorized):
            # Неверный токен бота
            logger.critical(f"Ошибка авторизации бота: {error}")
            return
            
        # Логируем ошибку
        logger.error(
            "Исключение при обработке обновления %s",
            update,
            exc_info=error
        )
        
        # Отправляем уведомление администраторам
        if isinstance(update, Update):
            await self._send_error_notification(error, update)
        else:
            await self._send_error_notification(error)
    
    def retry_on_error(self, max_retries: int = None, delay: int = None):
        """
        Декоратор для повторных попыток выполнения функции при возникновении ошибок.
        
        Args:
            max_retries: Максимальное количество попыток (по умолчанию из настроек)
            delay: Задержка между попытками в секундах (по умолчанию из настроек)
        """
        if max_retries is None:
            max_retries = settings.TELEGRAM_RETRY_ATTEMPTS
        if delay is None:
            delay = settings.TELEGRAM_RETRY_DELAY
        
        def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        return await func(*args, **kwargs)
                    except (NetworkError, TimedOut) as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.warning(
                                "Сетевая ошибка (попытка %d/%d), повтор через %dс: %s",
                                attempt + 1, max_retries, delay, e
                            )
                            await asyncio.sleep(delay)
                    except RetryAfter as e:
                        last_error = e
                        wait_time = e.retry_after
                        logger.warning(
                            "Превышен лимит запросов (попытка %d/%d), ожидание %dс",
                            attempt + 1, max_retries, wait_time
                        )
                        await asyncio.sleep(wait_time)
                    except Exception as e:
                        last_error = e
                        logger.error(
                            "Ошибка при выполнении функции %s (попытка %d/%d): %s",
                            func.__name__, attempt + 1, max_retries, e,
                            exc_info=True
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay)
                
                # Если все попытки исчерпаны, логируем и пробрасываем последнее исключение
                logger.error(
                    "Превышено максимальное количество попыток (%d) для функции %s",
                    max_retries, func.__name__
                )
                raise last_error if last_error else Exception("Неизвестная ошибка")
            
            return wrapper
        return decorator


error_handler = TelegramErrorHandler()


def setup_error_handlers(application) -> None:
    """Настройка обработчиков ошибок для приложения."""
    error_handler.bot = application.bot
    application.add_error_handler(error_handler.handle_error)
