"""
Сервис для работы с кэшированием в Redis.
Предоставляет удобный интерфейс для кэширования данных с автоматической сериализацией/десериализацией.
"""
import json
import pickle
from datetime import timedelta
from typing import Any, Optional, TypeVar, Type, Callable, Awaitable

from fastapi import Depends
from fastapi.encoders import jsonable_encoder

from app.core.redis import get_redis, redis_manager

T = TypeVar('T')

class CacheService:
    """Сервис для работы с кэшированием в Redis."""
    
    def __init__(self, redis=Depends(get_redis)):
        self.redis = redis
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение из кэша по ключу.
        
        :param key: Ключ кэша
        :param default: Значение по умолчанию, если ключ не найден
        :return: Раскодированное значение или default
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
                
            # Пытаемся десериализовать JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Если не JSON, возвращаем как есть
                return value
        except Exception as e:
            logger.error(f"Ошибка при получении значения из кэша: {e}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Установить значение в кэш.
        
        :param key: Ключ кэша
        :param value: Значение для кэширования
        :param expire: Время жизни в секундах
        :return: True в случае успеха, иначе False
        """
        try:
            # Сериализуем значение в JSON, если это возможно
            try:
                value = json.dumps(jsonable_encoder(value))
            except (TypeError, OverflowError):
                # Если не сериализуется в JSON, используем pickle
                value = pickle.dumps(value)
            
            if expire:
                return await self.redis.setex(key, expire, value)
            return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """
        Удалить ключи из кэша.
        
        :param keys: Ключи для удаления
        :return: Количество удаленных ключей
        """
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Ошибка при удалении из кэша: {e}")
            return 0
    
    async def get_or_set(
        self, 
        key: str, 
        default: Any = None,
        expire: Optional[int] = None,
        setter: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> Any:
        """
        Получить значение из кэша, если его нет - установить и вернуть.
        
        :param key: Ключ кэша
        :param default: Значение по умолчанию, если ключ не найден
        :param expire: Время жизни в секундах
        :param setter: Функция для получения значения, если его нет в кэше
        :return: Значение из кэша или установленное значение
        """
        value = await self.get(key)
        if value is not None:
            return value
            
        if setter is not None:
            value = await setter()
        elif default is not None:
            value = default
        else:
            return None
            
        await self.set(key, value, expire)
        return value
    
    async def clear_all(self) -> bool:
        """Очистить весь кэш."""
        try:
            return await self.redis.flushdb()
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")
            return False

# Создаем экземпляр сервиса для удобного импорта
cache_service = CacheService()

# Функция для внедрения зависимости
def get_cache_service() -> CacheService:
    """Возвращает экземпляр сервиса кэширования."""
    return cache_service
