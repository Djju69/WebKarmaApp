"""
Модуль для тестирования кэширования.
Временно отключен для отладки 2FA.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.services.cache_service import CacheService, get_cache_service
from app.core.config import settings

router = APIRouter()

@router.get("/test-cache")
async def test_cache():
    """
    Тестовый эндпоинт для проверки работы кэширования.
    Временно отключено.
    """
    return {"message": "Cache is temporarily disabled for debugging"}
    
    # Временно закомментировано для отладки 2FA
    # @cache(expire=60)  # Кэшируем на 60 секунд
    # async def test_cache():
    #     return {"current_time": datetime.utcnow().isoformat()}

@router.get("/get-value/{key}")
async def get_value(
    key: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Получить значение из кэша по ключу.
    """
    value = await cache_service.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": value}

@router.post("/set-value/{key}")
async def set_value(
    key: str,
    value: str,
    expire: int = settings.REDIS_CACHE_EXPIRE,
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Установить значение в кэш.
    
    :param key: Ключ
    :param value: Значение
    :param expire: Время жизни в секундах (по умолчанию из настроек)
    """
    result = await cache_service.set(key, value, expire)
    return {"success": result, "key": key, "expire_seconds": expire}

@router.delete("/delete-value/{key}")
async def delete_value(
    key: str,
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Удалить значение из кэша по ключу.
    """
    result = await cache_service.delete(key)
    return {"success": bool(result), "deleted_count": result}

@router.get("/cache-stats")
async def cache_stats(
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Получить статистику по кэшу.
    """
    # Получаем все ключи (осторожно с большими базами!)
    keys = await cache_service.redis.keys("*")
    return {
        "keys_count": len(keys),
        "keys": keys[:100]  # Возвращаем только первые 100 ключей
    }
