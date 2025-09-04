"""
Tests for Redis integration.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.redis import redis_manager
from app.services.cache_service import CacheService

# Test client
client = TestClient(app)

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def cleanup_redis():
    """Clean up Redis before each test."""
    await redis_manager.init_redis_cache()
    await redis_manager._redis.flushdb()
    yield
    await redis_manager._redis.flushdb()

@pytest.mark.asyncio
async def test_redis_connection():
    """Test that we can connect to Redis."""
    # Initialize Redis
    redis = await redis_manager.get_redis()
    
    # Test connection by setting and getting a value
    test_key = "test:connection"
    test_value = "test_value"
    
    # Set value
    await redis.set(test_key, test_value)
    
    # Get value
    value = await redis.get(test_key)
    
    assert value == test_value, "Failed to get the same value from Redis"

@pytest.mark.asyncio
async def test_cache_service_basic_operations():
    """Test basic operations of CacheService."""
    cache_service = CacheService()
    
    # Test set and get
    test_key = "test:key"
    test_value = {"hello": "world"}
    
    # Set value
    result = await cache_service.set(test_key, test_value, expire=60)
    assert result is True, "Failed to set value in cache"
    
    # Get value
    value = await cache_service.get(test_key)
    assert value == test_value, "Failed to get the same value from cache"
    
    # Delete value
    deleted = await cache_service.delete(test_key)
    assert deleted == 1, "Failed to delete value from cache"
    
    # Get non-existent value
    value = await cache_service.get("non_existent_key")
    assert value is None, "Non-existent key should return None"

@pytest.mark.asyncio
async def test_cache_endpoints():
    """Test the cache API endpoints."""
    # Test setting a value
    test_key = "test:api:key"
    test_value = "test_api_value"
    
    # Set value
    response = client.post(
        f"/cache/set-value/{test_key}",
        json={"value": test_value},
        params={"expire": 60}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Get value
    response = client.get(f"/cache/get-value/{test_key}")
    assert response.status_code == 200
    assert response.json()["value"] == test_value
    
    # Delete value
    response = client.delete(f"/cache/delete-value/{test_key}")
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Get non-existent value should return 404
    response = client.get(f"/cache/get-value/{test_key}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_cache_decorator():
    """Test the @cache decorator."""
    # First request - should be cached
    response1 = client.get("/cache/test-cache")
    assert response1.status_code == 200
    first_time = response1.json()["current_time"]
    
    # Second request - should return cached value
    response2 = client.get("/cache/test-cache")
    assert response2.status_code == 200
    second_time = response2.json()["current_time"]
    
    assert first_time == second_time, "Cached response should return the same value"

@pytest.mark.asyncio
async def test_cache_service_get_or_set():
    """Test the get_or_set method of CacheService."""
    cache_service = CacheService()
    test_key = "test:get_or_set"
    
    # Value doesn't exist - should use default
    value = await cache_service.get_or_set(test_key, default="default_value")
    assert value == "default_value"
    
    # Value exists - should return cached value
    value = await cache_service.get_or_set(test_key, default="new_default")
    assert value == "default_value"
    
    # Test with setter function
    async def get_data():
        return "data_from_setter"
    
    value = await cache_service.get_or_set("test:setter", setter=get_data)
    assert value == "data_from_setter"
    
    # Cleanup
    await cache_service.delete(test_key, "test:setter")
