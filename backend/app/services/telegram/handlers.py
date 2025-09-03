"""
Telegram update handlers.
"""
import logging
from typing import Dict, Any, Callable, Awaitable, Optional, List, Type, TypeVar, Union

from telegram import Update, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler as TgCommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
from telegram.error import TelegramError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from .error_handling import error_handler

# Import command handlers
from .handlers.loyalty_commands import register_handlers as register_loyalty_handlers

logger = logging.getLogger(__name__)

# Type variables for better type hints
T = TypeVar('T')
TelegramUpdate = Union[Update, CallbackQuery, Message]

class CommandHandler:
    """Handler for bot commands."""
    
    def __init__(self):
        self.commands: Dict[str, Callable[[TelegramMessage], Awaitable[None]]] = {}
    
    def command(self, name: str):
        """Decorator to register a command handler."""
        def decorator(func: Callable[[TelegramMessage], Awaitable[None]]):
            self.commands[name] = func
            return func
        return decorator
    
    async def handle_message(self, message: TelegramMessage):
        """Handle an incoming message and route it to the appropriate command handler."""
        if not message.text or not message.text.startswith('/'):
            return
            
        # Extract command and arguments
        parts = message.text.split()
        command = parts[0][1:].split('@')[0]  # Remove '/' and bot username if present
        args = parts[1:] if len(parts) > 1 else []
        
        # Find and call the appropriate handler
        if command in self.commands:
            try:
                await self.commands[command](message)
            except Exception as e:
                logger.error(f"Error handling command /{command}: {e}")
                async with TelegramClient() as client:
                    await client.send_message(
                        chat_id=message.chat.id,
                        text="❌ Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
                    )

# Global application instance
_application: Optional[Application] = None

def get_application() -> Application:
    """Get the global application instance."""
    global _application
    if _application is None:
        raise RuntimeError("Application not initialized. Call create_application() first.")
    return _application

def create_application() -> Application:
    """Create and configure the Telegram application."""
    global _application
    if _application is not None:
        return _application
        
    logger.info("Creating new Telegram application...")
    
    # Create application with persistence
    _application = Application.builder()\
        .token(settings.TELEGRAM_BOT_TOKEN)\
        .build()
    
    # Register handlers
    register_handlers(_application)
    
    # Set up error handling
    error_handler.setup_error_handlers(_application)
    
    logger.info("Telegram application created successfully")
    return _application

# Global command handler instance
command_handler = CommandHandler()

# Initialize application
application = create_application()

async def register_handlers(application: Application) -> None:
    """
    Register all update handlers with the application.
    
    Args:
        application: The Telegram application instance
    """
    logger.info("Registering Telegram handlers...")
    
    # Register command handlers
    application.add_handler(TgCommandHandler("start", handle_start_command))
    application.add_handler(TgCommandHandler("help", handle_help_command))
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Register message handler (for non-command messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message_update
    ))
    
    # Register loyalty command handlers
    register_loyalty_handlers(application)
    
    logger.info("All Telegram handlers registered")

# Example command handlers
@error_handler.retry_on_error()
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    
    Args:
        update: The incoming update
        context: The context object
    """
    if not update.effective_user or not update.effective_chat:
        logger.warning("Received update without user or chat information")
        return
        
    db = SessionLocal()
    try:
        logger.info(f"Processing /start command from user {update.effective_user.id}")
        
        # Register or get user
        user = db.query(User).filter(
            User.telegram_id == update.effective_user.id
        ).first()
        
        is_new_user = False
        if not user:
            is_new_user = True
            user = User(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
                is_active=True
            )
            db.add(user)
            db.commit()
            logger.info(f"New user registered: {user.telegram_id} (@{user.username})")
        
        # Prepare welcome message
        if is_new_user:
            welcome_text = (
                f"👋 Привет, {update.effective_user.first_name or 'друг'}!\n\n"
                "Я бот системы лояльности KarmaSystem. Я помогу вам узнать ваш баланс бонусов, "
                "историю операций и многое другое.\n\n"
                "Используйте команду /help, чтобы увидеть список доступных команд."
            )
        else:
            welcome_text = (
                f"👋 С возвращением, {update.effective_user.first_name or 'друг'}!\n\n"
                "Чем могу помочь? Используйте команду /help для списка доступных команд."
                "Используйте /help для просмотра доступных команд."
            )
            
        await update.message.reply_text(welcome_text)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
        )
    finally:
        db.close()

@command_handler.command("help")
async def handle_help_command(update: Update, context: CallbackContext) -> None:
    """Handle /help command."""
    if context.args and len(context.args) > 0:
        # Show help for specific command
        command = context.args[0].lower()
        help_texts = {
            'balance': (
                "💎 *Баланс баллов*\n\n"
                "Показывает текущий баланс бонусных баллов, уровень лояльности и доступные привилегии.\n\n"
                "Использование: /balance"
            ),
            'earn': (
                "➕ *Начисление баллов* (админ)\n\n"
                "Начисляет указанное количество баллов пользователю.\n\n"
                "Использование: /earn <количество_баллов> [комментарий]\n\n"
                "Пример: /earn 100 За регистрацию"
            ),
            'spend': (
                "➖ *Списание баллов*\n\n"
                "Списывает указанное количество баллов с баланса пользователя.\n\n"
                "Использование: /spend <количество_баллов> [комментарий]\n\n"
                "Пример: /spend 50 Оплата заказа #123"
            ),
            'history': (
                "📜 *История операций*\n\n"
                "Показывает последние операции по вашему счёту.\n\n"
                "Использование: /history"
            )
        }
    
    Args:
        update: The incoming update
        context: The context object
    """
    if not update.effective_chat:
        logger.warning("Received help command without chat information")
        return
        
    try:
        logger.info(f"Processing /help command in chat {update.effective_chat.id}")
        
        help_text = (
            "📚 *Доступные команды:*\n\n"
            "🔹 /start - Начать работу с ботом\n"
            "🔹 /help - Показать это сообщение\n"
            "🔹 /balance - Показать баланс бонусов\n"
            "🔹 /earn - Начислить бонусы (только для администраторов)\n"
            "🔹 /spend - Потратить бонусы\n"
            "🔹 /history - История операций\n"
            "🔹 /profile - Мой профиль\n\n"
            "💡 Вы также можете использовать кнопки внизу экрана для быстрого доступа к основным функциям."
        )
        
        # Create inline keyboard with quick actions
        keyboard = [
            [
                InlineKeyboardButton("💳 Баланс", callback_data="balance"),
                InlineKeyboardButton("📊 История", callback_data="history")
            ],
            [
                InlineKeyboardButton("👤 Профиль", callback_data="profile"),
                InlineKeyboardButton("❓ Помощь", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in help command: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Не удалось загрузить справку. Пожалуйста, попробуйте позже."
        )

async def handle_message_update(update: Dict[str, Any]):
    """Handle incoming message updates."""
    try:
        # Convert to Telegram Update object
        tg_update = Update.de_json(update, application.bot)
        
        # Handle commands
        if tg_update.message and tg_update.message.text and tg_update.message.text.startswith('/'):
            await application.process_update(tg_update)
            
    except Exception as e:
        logger.error(f"Error handling message update: {e}")
        
        # Try to send error message to user
        try:
            if tg_update and tg_update.effective_chat:
                await tg_update.effective_chat.send_message(
                    "❌ Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

async def handle_callback_query(update: Dict[str, Any]):
    """Handle callback queries from inline keyboards."""
    try:
        # Convert to Telegram Update object
        tg_update = Update.de_json(update, application.bot)
        
        # Process callback query
        if tg_update.callback_query:
            await application.process_update(tg_update)
            
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        
        # Try to send error message to user
        try:
            if tg_update and tg_update.effective_chat:
                await tg_update.effective_chat.send_message(
                    "❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте ещё раз."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

def register_handlers() -> Dict[str, Callable]:
    """
    Register all update handlers.
    
    Returns:
        Dict mapping update types to handler functions
    """
    # Register command handlers
    command_handler.register("start", handle_start_command)
    command_handler.register("help", handle_help_command)
    
    # Register command handlers with python-telegram-bot
    application.add_handler(TgCommandHandler("start", handle_start_command))
    application.add_handler(TgCommandHandler("help", handle_help_command))
    
    # Register error handler
    async def error_handler(update: object, context: CallbackContext) -> None:
        """Log errors caused by updates and handle them."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        # Notify user about the error
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
            )
    
    application.add_error_handler(error_handler)
    
    return {
        "message": handle_message_update,
        "callback_query": handle_callback_query,
    }
