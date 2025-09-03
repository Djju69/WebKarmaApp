#!/usr/bin/env python3
"""
Script to set up Telegram webhook.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.telegram import setup_webhook

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Set up the Telegram webhook."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables")
        return
    
    if not settings.TELEGRAM_WEBHOOK_URL:
        logger.error("TELEGRAM_WEBHOOK_URL is not set in environment variables")
        return
    
    try:
        logger.info("Setting up Telegram webhook...")
        result = await setup_webhook(
            url=str(settings.TELEGRAM_WEBHOOK_URL),
            secret_token=settings.TELEGRAM_SECRET_TOKEN
        )
        
        if result:
            logger.info("Webhook set up successfully!")
        else:
            logger.error("Failed to set up webhook")
            
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
