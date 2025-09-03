"""
Webhook setup and verification for Telegram Bot API.
"""
import hmac
import hashlib
from typing import Optional, Dict, Any, Callable, Awaitable
from fastapi import Request, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, HttpUrl
from app.core.config import settings
from .client import TelegramClient

class WebhookConfig(BaseModel):
    """Webhook configuration model."""
    url: HttpUrl
    secret_token: Optional[str] = None
    max_connections: int = 40
    allowed_updates: Optional[list[str]] = None
    drop_pending_updates: bool = True

async def setup_webhook(url: str, secret_token: Optional[str] = None) -> bool:
    """
    Set up webhook with Telegram Bot API.
    
    Args:
        url: Full URL where Telegram will send updates
        secret_token: Optional secret token for webhook verification
        
    Returns:
        bool: True if webhook was set up successfully
    """
    async with TelegramClient() as client:
        # First, delete any existing webhook
        await client.delete_webhook()
        
        # Set new webhook
        result = await client.set_webhook(
            url=url,
            secret_token=secret_token
        )
        
        return result

def verify_telegram_webhook(request: Request) -> bool:
    """
    Verify Telegram webhook request using secret token.
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if request is verified
    """
    if not settings.TELEGRAM_SECRET_TOKEN:
        return True  # Skip verification if no secret token is set
    
    # Get the secret token from the request headers
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    
    if not secret_token or not hmac.compare_digest(
        secret_token,
        settings.TELEGRAM_SECRET_TOKEN
    ):
        return False
        
    return True

def create_telegram_router(
    update_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]]
) -> APIRouter:
    """
    Create FastAPI router for Telegram webhook.
    
    Args:
        update_handlers: Dictionary mapping update types to handler functions
        
    Returns:
        APIRouter: Configured FastAPI router
    """
    router = APIRouter()
    
    @router.post("/webhook/{bot_token}")
    @router.post("/webhook/")
    async def handle_webhook(
        update: Dict[str, Any],
        request: Request,
        bot_token: Optional[str] = None
    ) -> Dict[str, str]:
        """Handle incoming Telegram updates."""
        # Verify webhook secret if configured
        if settings.TELEGRAM_SECRET_TOKEN and not verify_telegram_webhook(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret token"
            )
            
        # Handle different types of updates
        update_type = None
        if 'message' in update:
            update_type = 'message'
        elif 'callback_query' in update:
            update_type = 'callback_query'
        # Add more update types as needed
            
        # Call the appropriate handler if registered
        if update_type in update_handlers:
            try:
                await update_handlers[update_type](update)
            except Exception as e:
                # Log the error but don't expose details to the client
                print(f"Error handling {update_type} update: {e}")
                return {"status": "error", "message": "Error processing update"}
                
        return {"status": "ok"}
    
    return router
