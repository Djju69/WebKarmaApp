"""
Main application module for the KarmaSystem Bot.
"""
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core configuration
from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Import API routers
from app.api.v1.api import api_router as v1_router
from app.api.api import api_router as base_router

# Import Telegram services
from app.services.telegram import (
    create_application as create_telegram_app,
    setup_error_handlers,
    get_application as get_telegram_application
)
from app.api.v1.endpoints.telegram import bot_application

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Telegram bot
    if settings.TELEGRAM_BOT_TOKEN:
        # Create and configure Telegram application
        telegram_app = create_telegram_app()
        
        # Register handlers
        register_handlers(telegram_app)
        
        # Set the global bot_application reference
        global bot_application
        bot_application = telegram_app
        
        # Set webhook if enabled
        if settings.TELEGRAM_WEBHOOK_ENABLED and settings.TELEGRAM_WEBHOOK_URL:
            webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/api/v1/telegram/webhook/{settings.TELEGRAM_WEBHOOK_SECRET}"
            await telegram_app.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
                drop_pending_updates=True
            )
            logging.info(f"Telegram webhook set to: {webhook_url}")
        else:
            # Use polling if webhook is disabled
            await telegram_app.initialize()
            await telegram_app.start()
            logging.info("Telegram bot started in polling mode")
    
    yield
    
    # Shutdown: Clean up resources
    if settings.TELEGRAM_BOT_TOKEN and not settings.TELEGRAM_WEBHOOK_ENABLED:
        await telegram_app.stop()
        await telegram_app.shutdown()

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    # In production, replace "*" with specific origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    application.include_router(
        base_router,
        prefix=settings.API_V1_STR
    )
    application.include_router(
        v1_router,
        prefix=f"{settings.API_V1_STR}/v1"
    )
    
    # Setup Telegram webhook if configured
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_WEBHOOK_URL:
        try:
            # Create and include Telegram router
            telegram_router = create_telegram_router({
                'message': handle_message_update,
                'callback_query': handle_callback_query,
            })
            app.include_router(telegram_router, prefix="/telegram", tags=["telegram"])
            
            # Set webhook on startup
            @app.on_event("startup")
            async def on_startup():
                await setup_webhook(
                    url=str(settings.TELEGRAM_WEBHOOK_URL),
                    secret_token=settings.TELEGRAM_SECRET_TOKEN
                )
                logger.info("Telegram webhook configured successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup Telegram webhook: {e}")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN)
        }
    
    # Example protected endpoint
    @app.get("/api/me")
    async def read_users_me(current_user: dict = Depends(get_current_user)):
        return current_user
    
    return app

# Create the FastAPI application
app = create_application()

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Initialize Telegram bot application
try:
    telegram_app = get_telegram_application()
    setup_error_handlers(telegram_app)
    logger.info("Telegram application initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize Telegram application: {e}", exc_info=True)
    raise

# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

# Models (temporary, will be moved to schemas)
class TokenData(BaseModel):
    username: Optional[str] = None

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Application entry point
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
