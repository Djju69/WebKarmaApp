"""
Telegram API client implementation.
"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, HttpUrl
from app.core.config import settings

logger = logging.getLogger(__name__)

class TelegramUser(BaseModel):
    """Telegram user model."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False

class TelegramChat(BaseModel):
    """Telegram chat model."""
    id: int
    type: str  # private, group, supergroup, channel
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class TelegramMessage(BaseModel):
    """Telegram message model."""
    message_id: int
    from_user: Optional[TelegramUser] = None
    chat: TelegramChat
    date: int
    text: Optional[str] = None

class TelegramUpdate(BaseModel):
    """Telegram update model."""
    update_id: int
    message: Optional[TelegramMessage] = None
    callback_query: Optional[Dict[str, Any]] = None

class TelegramClient:
    """Client for interacting with Telegram Bot API."""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, token: str = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("Telegram bot token is required")
        self.base_url = self.BASE_URL.format(token=self.token)
        self.session = httpx.AsyncClient()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def _make_request(self, method: str, **params) -> Dict[str, Any]:
        """Make request to Telegram Bot API."""
        url = f"{self.base_url}/{method}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                result = response.json()
                
                if not result.get('ok'):
                    error_msg = result.get('description', 'Unknown error')
                    logger.error(f"Telegram API error: {error_msg}")
                    raise Exception(f"Telegram API error: {error_msg}")
                    
                return result.get('result')
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request to Telegram API: {e}")
            raise
    
    async def get_me(self) -> Dict[str, Any]:
        """Get information about the bot."""
        return await self._make_request('getMe')
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = 'HTML',
        reply_markup: Optional[Dict] = None,
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """Send message to a chat."""
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview
        }
        if reply_markup:
            params['reply_markup'] = reply_markup
            
        return await self._make_request('sendMessage', **params)
    
    async def set_webhook(self, url: str, secret_token: Optional[str] = None) -> bool:
        """Set webhook URL for receiving updates."""
        params = {'url': url}
        if secret_token:
            params['secret_token'] = secret_token
            
        result = await self._make_request('setWebhook', **params)
        return result

    async def delete_webhook(self) -> bool:
        """Remove webhook integration."""
        result = await self._make_request('deleteWebhook')
        return result
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook status."""
        return await self._make_request('getWebhookInfo')

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
        url: Optional[str] = None,
        cache_time: int = 0
    ) -> bool:
        """Send answers to callback queries."""
        params = {
            'callback_query_id': callback_query_id,
            'show_alert': show_alert,
            'cache_time': cache_time
        }
        if text:
            params['text'] = text
        if url:
            params['url'] = url
            
        return await self._make_request('answerCallbackQuery', **params)
