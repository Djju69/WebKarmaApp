"""
Инициализация и настройка Telegram бота.
"""
import logging
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    Defaults,
    PicklePersistence,
)

from app.core.config import settings
from app.services.telegram.handlers import register_handlers
from app.services.telegram.error_handling import setup_error_handlers, error_handler

logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Создать и настроить приложение Telegram бота."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("Не задан TELEGRAM_BOT_TOKEN в настройках")

    logger.info("Инициализация Telegram бота...")
    
    # Настройки по умолчанию
    defaults = Defaults(
        parse_mode="HTML",
        disable_web_page_preview=True,
        allow_sending_without_reply=True,
    )
    
    # Создаем приложение с настройками
    builder = Application.builder()
    builder.token(settings.TELEGRAM_BOT_TOKEN)
    builder.defaults(defaults)
    
    # Настройка персистентности (если нужно)
    if settings.ENVIRONMENT != "test":
        builder.persistence(
            PicklePersistence(
                filepath="data/telegram_bot_persistence.pickle",
                store_data={
                    "user_data": True,
                    "chat_data": True,
                    "bot_data": True,
                    "callback_data": True,
                },
            )
        )
    
    # Создаем приложение
    application = builder.build()
    
    # Настраиваем обработчики
    register_handlers(application)
    
    # Настраиваем обработку ошибок
    setup_error_handlers(application)
    
    # Устанавливаем обработчик для необработанных команд
    async def unknown_command(update: Update, context: CallbackContext) -> None:
        """Обработчик неизвестных команд."""
        if update.effective_message:
            await update.effective_message.reply_text(
                "Извините, я не понимаю эту команду. Введите /help для списка доступных команд."
            )
    
    # Добавляем обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND & ~filters.ChatType.PRIVATE, unknown_command))
    
    # Настраиваем команды бота
    if settings.TELEGRAM_BOT_COMMANDS:
        commands = [
            BotCommand(command=cmd, description=desc)
            for cmd, desc in settings.TELEGRAM_BOT_COMMANDS.items()
        ]
        
        async def set_bot_commands():
            try:
                await application.bot.set_my_commands(commands)
                logger.info("Команды бота успешно обновлены")
            except Exception as e:
                logger.error(f"Ошибка при установке команд бота: {e}")
        
        # Запускаем задачу на установку команд
        application.create_task(set_bot_commands())
    
    logger.info("Telegram бот инициализирован")
    return application


# Глобальная переменная для хранения экземпляра приложения
_application: Optional[Application] = None


def get_application() -> Application:
    """Получить экземпляр приложения Telegram бота."""
    global _application
    if _application is None:
        _application = create_application()
    return _application
