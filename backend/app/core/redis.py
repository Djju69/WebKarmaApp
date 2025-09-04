from typing import Optional
import redis.asyncio as redis
from fastapi import Depends
# Temporarily disabled for debugging
# from fastapi_cache import FastAPICache
# from fastapi_cache.backends.redis import RedisBackend
# from fastapi_cache.decorator import cache

from app.core.config import settings

class RedisManager:
    _instance = None
    _redis: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance

    async def init_redis_cache(self):
        """Инициализация Redis для кэширования"""
        if not self._redis:
            self._redis = redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True,
                db=settings.REDIS_DB
            )
            # Temporarily disabled for debugging
            # FastAPICache.init(RedisBackend(self._redis), prefix="fastapi-cache")
        return self._redis

    async def get_redis(self) -> redis.Redis:
        """Получение экземпляра Redis"""
        if not self._redis:
            await self.init_redis_cache()
        return self._redis

    async def close(self):
        """Закрытие соединения с Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None

# Создаем глобальный экземпляр менеджера Redis
redis_manager = RedisManager()

# Зависимость для внедрения Redis в эндпоинты
async def get_redis() -> redis.Redis:
    """Зависимость для внедрения Redis в эндпоинты FastAPI"""
    return await redis_manager.get_redis()

# Декоратор для кэширования результатов функций
# Пример использования:
# @cached(expire=60)  # кэшировать на 60 секунд
# async def get_some_data():
#     return {"data": "some_data"}
def cached(expire: int = 60):
    """
    Декоратор для кэширования результатов функций
    :param expire: время жизни кэша в секундах
    """
    return cache(expire=expire)
