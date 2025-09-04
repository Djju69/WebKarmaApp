"""
Конфигурация и фикстуры для тестирования.
"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.db.base import Base
from app.main import create_application

# Настройки для тестов
test_settings = Settings(
    DEBUG=True,
    ENVIRONMENT="testing",
    SQLITE_DB="sqlite:///./test.db",
    DATABASE_URI="sqlite:///./test.db",
    # Используем локальный Redis с несуществующим хостом, чтобы тесты не подключались к реальному Redis
    REDIS_HOST="localhost.test",
    REDIS_PORT=6379,
    REDIS_DB=0,
    REDIS_PASSWORD="",
    # Отключаем внешние сервисы для тестов
    SENTRY_DSN=None,
    OTEL_EXPORTER_OTLP_ENDPOINT=None,
    # Упрощаем логирование для тестов
    LOG_LEVEL="WARNING"
)

# Переопределяем глобальные настройки
import app.core.config as config_module
config_module.settings = test_settings

# URL тестовой базы данных
SQLALCHEMY_DATABASE_URL = test_settings.DATABASE_URI

# Создаем тестовый движок базы данных
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения тестовой сессии БД
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Мок для Redis
class MockRedis:
    def __init__(self, *args, **kwargs):
        self.data = {}
        
    async def get(self, key):
        return self.data.get(key)
        
    async def set(self, key, value, ex=None):
        self.data[key] = value
        return True
        
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True
        
    async def exists(self, key):
        return key in self.data
        
    # Add other Redis methods that might be used
    async def ping(self):
        return True
        
    async def close(self):
        pass

# Мок для Redis Manager
class MockRedisManager:
    def __init__(self):
        self.redis = MockRedis()
        self.is_connected = True
        
    async def init_redis_cache(self):
        self.is_connected = True
        return self.redis
        
    async def close_redis(self):
        self.is_connected = False
        
    def get_redis(self):
        return self.redis

# Создаем тестовое приложение
def create_test_application():
    # Импортируем здесь, чтобы избежать циклического импорта
    from fastapi import Depends, FastAPI
    from sqlalchemy.orm import Session
    
    # Создаем тестовое приложение
    app = FastAPI()
    
    # Мокируем Redis
    app.state.redis_manager = MockRedisManager()
    
    # Простой эндпоинт для проверки работы
    @app.get("/test")
    def test_endpoint():
        return {"message": "Test endpoint is working"}
        
    # Переопределяем зависимости
    from app.core.deps import get_db as original_get_db
    app.dependency_overrides[original_get_db] = override_get_db
    
    # Импортируем и подключаем основные роутеры
    from app.api.v1.api import api_router as v1_router
    from app.api.endpoints import auth as auth_router
    from app.api.endpoints import two_factor_router
    
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(auth_router.router, prefix="/auth")
    app.include_router(two_factor_router, prefix="/2fa")
    
    return app

# Создаем тестовое приложение
app = create_test_application()

# Мокаем Redis на уровне модуля
import sys
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

# Патчим redis на уровне модуля, чтобы перехватить все вызовы
sys.modules['redis'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()

# Создаем мок для Redis клиента с поддержкой синхронных и асинхронных операций
class MockRedisClient:
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.ping = AsyncMock(return_value=True)
        
    # Синхронные методы
    def get(self, key, *args, **kwargs):
        return self.data.get(key)
        
    def set(self, key, value, *args, **kwargs):
        self.data[key] = value
        return True
        
    def delete(self, key, *args, **kwargs):
        if key in self.data:
            del self.data[key]
        return True
        
    def exists(self, key, *args, **kwargs):
        return key in self.data
        
    # Асинхронные методы
    async def aget(self, key, *args, **kwargs):
        return self.get(key, *args, **kwargs)
        
    async def aset(self, key, value, *args, **kwargs):
        return self.set(key, value, *args, **kwargs)
        
    async def adelete(self, key, *args, **kwargs):
        return self.delete(key, *args, **kwargs)
        
    async def aexists(self, key, *args, **kwargs):
        return self.exists(key, *args, **kwargs)
        
    # Поддержка вызова как асинхронного контекстного менеджера
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    # Поддержка Redis pipeline
    def pipeline(self):
        return MockRedisPipeline(self)

# Класс для эмуляции Redis pipeline
class MockRedisPipeline:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.commands = []
        self.results = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def incr(self, key, amount=1):
        self.commands.append(('incr', key, amount))
        # Возвращаем self для поддержки цепочки вызовов
        return self
        
    def expire(self, key, time):
        self.commands.append(('expire', key, time))
        return self
        
    def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'incr':
                key = cmd[1]
                amount = cmd[2]
                current = int(self.redis.get(key) or 0)
                new_val = current + amount
                self.redis.set(key, str(new_val))
                results.append(new_val)
            elif cmd[0] == 'expire':
                # В тестах просто игнорируем expire
                results.append(True)
        self.commands = []
        return results

# Создаем мок для redis_manager с поддержкой синхронных и асинхронных операций
class MockRedisManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.redis = MockRedisClient()
            cls._instance.is_connected = True
        return cls._instance
    
    async def init_redis_cache(self):
        self.is_connected = True
        return self.redis
        
    async def close_redis(self):
        self.is_connected = False
        
    def get_redis(self):
        return self.redis
        
    # Добавляем алиасы для асинхронных методов, если они используются
    async def aget(self, key, *args, **kwargs):
        return self.redis.get(key, *args, **kwargs)
        
    async def aset(self, key, value, *args, **kwargs):
        return self.redis.set(key, value, *args, **kwargs)
        
    async def adelete(self, key, *args, **kwargs):
        return self.redis.delete(key, *args, **kwargs)
        
    async def aexists(self, key, *args, **kwargs):
        return self.redis.exists(key, *args, **kwargs)

# Применяем патчи
mock_redis_manager = MockRedisManager()

# Применяем патчи
mock_redis_manager = MockRedisManager()

# Импортируем redis_manager, чтобы заменить его на мок
from app.core.redis import redis_manager as actual_redis_manager
actual_redis_manager.redis = mock_redis_manager.redis

# Устанавливаем мок в приложение
app.state.redis_manager = mock_redis_manager

# Мокаем Redis в security модуле
import app.core.security as security
security.redis_client = mock_redis_manager.redis

# Создаем таблицы в тестовой базе данных
@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Фикстура для создания и удаления тестовой базы данных."""
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    # Патчим Redis для всех тестов
    with patch('app.core.redis.redis_manager', app.state.redis_manager):
        yield  # Тесты выполняются здесь
    
    # Удаляем все таблицы после выполнения тестов
    Base.metadata.drop_all(bind=engine)
    
    # Удаляем файл базы данных
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except PermissionError:
            # Игнорируем ошибки удаления файла в Windows
            pass

# Фикстура для тестового клиента
@pytest.fixture
def test_client():
    # Применяем патч для Redis в каждом тесте
    with patch('app.core.redis.redis_manager', app.state.redis_manager):
        with TestClient(app) as client:
            yield client

# Фикстура для сессии базы данных
@pytest.fixture
def db_session():
    """Фикстура для сессии базы данных."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Применяем патч для Redis в каждой сессии
    with patch('app.core.redis.redis_manager', app.state.redis_manager):
        yield session
    
    session.close()
    transaction.rollback()
    connection.close()

# Фикстура для тестового пользователя
# (Удалена дублирующаяся фикстура, используем полную реализацию ниже)
    
    # Cleanup is handled by the database session

# Fixture for test role
@pytest.fixture
def test_role(db_session, test_permissions):
    """Fixture to create a test role with permissions."""
    from app.models.user import Role, Permission
    
    # Create a test role if it doesn't exist
    role = db_session.query(Role).filter(Role.name == "test_role").first()
    
    if not role:
        role = Role(
            name="test_role",
            description="Test role for unit testing"
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
    
    # Required permissions for role management
    required_permissions = [
        test_permissions["role:create"],
        test_permissions["role:read"],
        test_permissions["role:update"],
        test_permissions["role:delete"],
        test_permissions["permission:read"],
    ]
    
    # Test permissions
    test_perm_list = [
        test_permissions["test:read"],
        test_permissions["test:write"],
        test_permissions["test:delete"],
    ]
    
    # Combine all permissions
    all_permissions = required_permissions + test_perm_list
    
    # Set permissions for the role
    role.permissions = all_permissions
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    
    return role

# Fixture for test permissions
@pytest.fixture
def test_permissions(db_session):
    """Fixture to create test permissions."""
    from app.models.user import Permission
    
    # Define all required permissions for role management
    permission_defs = [
        # Role management permissions (from RBAC decorators)
        {"name": "role:create", "description": "Create roles", "module": "auth"},
        {"name": "role:read", "description": "View roles", "module": "auth"},
        {"name": "role:update", "description": "Update roles", "module": "auth"},
        {"name": "role:delete", "description": "Delete roles", "module": "auth"},
        
        # Permission management
        {"name": "permission:read", "description": "View permissions", "module": "auth"},
        
        # Test permissions
        {"name": "test:read", "description": "Test read permission", "module": "test"},
        {"name": "test:write", "description": "Test write permission", "module": "test"},
        {"name": "test:delete", "description": "Test delete permission", "module": "test"},
    ]
    
    created_permissions = {}
    
    for perm_def in permission_defs:
        # Check if permission already exists
        permission = db_session.query(Permission).filter(
            Permission.name == perm_def["name"]
        ).first()
        
        if not permission:
            permission = Permission(**perm_def)
            db_session.add(permission)
            db_session.commit()
            db_session.refresh(permission)
        
        created_permissions[perm_def["name"]] = permission
    
    return created_permissions

# Fixture for test user with role
@pytest.fixture
def test_user(db_session, test_role, test_permissions):
    """Fixture to create a test user with admin role and all necessary permissions."""
    from app.core.security import get_password_hash
    from app.models.user import User, Role, Permission
    
    # Get all permissions from the test_permissions fixture
    all_permissions = list(test_permissions.values())
    
    # Create an admin role with all permissions if it doesn't exist
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator role")
        # Add all permissions to admin role
        admin_role.permissions = all_permissions
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)
    else:
        # Ensure the admin role has all permissions
        admin_role.permissions = all_permissions
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)
    
    # Create a test admin user if it doesn't exist
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    
    if not user:
        user = User(
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("adminpass"),
            is_active=True,
            is_verified=True
        )
        # Add admin role to the user
        user.roles = [admin_role]
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    # Ensure the user has the admin role with all permissions
    if admin_role not in user.roles:
        user.roles.append(admin_role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    # Ensure the admin role has all permissions
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    admin_role.permissions = all_permissions
    db_session.add(admin_role)
    db_session.commit()
    db_session.refresh(admin_role)
    
    # Refresh the user to get the latest role permissions
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    
    return user
