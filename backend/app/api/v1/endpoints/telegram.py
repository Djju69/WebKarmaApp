"""
Telegram Webhook API endpoints.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application

from app.core.config import settings
from app.services.telegram.handlers import register_handlers

router = APIRouter()
logger = logging.getLogger(__name__)

# This will be set when initializing the Telegram bot
bot_application: Application = None


def get_bot_application() -> Application:
    """Get the Telegram bot application instance."""
    if not bot_application:
        raise RuntimeError("Telegram bot application not initialized")
    return bot_application


@router.post("/webhook/{token}")
async def webhook(
    request: Request,
    token: str,
    bot_app: Application = Depends(get_bot_application)
) -> JSONResponse:
    """
    Handle incoming Telegram updates via webhook.
    
    Args:
        request: The incoming request
        token: The webhook token for verification
        bot_app: The Telegram bot application
        
    Returns:
        JSON response indicating success or failure
    """
    # Verify the webhook token
    if token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning(f"Invalid webhook token: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook token"
        )
    
    # Process the update
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot_app.bot)
        await bot_app.process_update(update)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error processing update"
        )


@router.get("/set-webhook")
async def set_webhook(bot_app: Application = Depends(get_bot_application)) -> Dict[str, Any]:
    """
    Set the Telegram webhook URL programmatically.
    
    This endpoint should be called during application startup or when the webhook URL changes.
    """
    if not settings.TELEGRAM_WEBHOOK_URL or not settings.TELEGRAM_WEBHOOK_SECRET:
        return {
            "status": "error",
            "message": "Webhook URL or secret not configured"
        }
    
    webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/{settings.TELEGRAM_WEBHOOK_SECRET}"
    
    try:
        await bot_app.bot.set_webhook(
            url=webhook_url,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        return {
            "status": "ok",
            "message": f"Webhook set to {webhook_url}",
            "url": webhook_url
        }
    except Exception as e:
        logger.error(f"Error setting webhook: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to set webhook: {str(e)}"
        }
