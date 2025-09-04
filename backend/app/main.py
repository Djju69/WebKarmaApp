"""
Главный модуль приложения KarmaSystem Bot.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, status, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Настройка логирования
from app.core.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Импорт конфигурации
from app.core.config import settings

# Инициализация Sentry
if settings.SENTRY_DSN:
    from app.core.monitoring import init_sentry
    init_sentry()
    logger.info("Sentry инициализирован")

# Инициализация метрик
from app.core.metrics import PrometheusMiddleware, metrics_router

# Импорт API роутеров
from app.api.v1.api import api_router as v1_router
from app.api.api import api_router as base_router
from app.api.endpoints import auth as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    Инициализирует Redis при запуске и корректно закрывает соединение при остановке.
    """
    # Код, выполняемый при запуске
    logger.info("Запуск приложения...")
    
    # Инициализация Redis
    from app.core.redis import redis_manager
    logger.info("Инициализация Redis...")
    await redis_manager.init_redis_cache()
    logger.info("Redis успешно инициализирован")
    
    try:
        yield  # Приложение работает
    finally:
        # Код, выполняемый при остановке
        logger.info("Остановка приложения...")
        # Закрываем соединение с Redis
        await redis_manager.close()
        logger.info("Соединение с Redis закрыто")

def create_application() -> FastAPI:
    """
    Создание и настройка FastAPI приложения.
    """
    # Настраиваем маршрутизацию с использованием кастомного класса маршрута
    route_class = None
    if settings.ENABLE_REQUEST_VALIDATION:
        from app.api.middleware import ValidatedRoute
        route_class = ValidatedRoute
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="API для KarmaSystem Bot",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.DEBUG,
        lifespan=lifespan,
        route_class=route_class
    )
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Добавляем middleware для метрик
    app.add_middleware(PrometheusMiddleware)
    
    # Настраиваем маршруты
    setup_routers(app)
    
    # Настраиваем обработчики исключений
    setup_exception_handlers(app)
    
    # Добавляем обработчик для проверки работоспособности
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.VERSION}
    
    return app

def setup_routers(app: FastAPI) -> None:
    """Настройка маршрутов API."""
    # Базовые маршруты
    app.include_router(base_router, prefix="")
    
    # API v1
    app.include_router(v1_router, prefix=f"{settings.API_V1_STR}/v1")
    
    # Аутентификация
    app.include_router(auth_router.router, prefix="/auth", tags=["Аутентификация"])
    
    # Метрики
    app.include_router(metrics_router, prefix="/metrics", tags=["Метрики"])
    
    # Проверка работоспособности
    @app.get("/health", status_code=status.HTTP_200_OK, tags=["Система"])
    async def health_check():
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG
        }

def setup_exception_handlers(app: FastAPI) -> None:
    """Настройка обработчиков исключений."""
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, 'headers', None)
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Необработанное исключение")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Внутренняя ошибка сервера"}
        )

# Создаем экземпляр приложения
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
