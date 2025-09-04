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
    DATABASE_URI="sqlite:///./test.db"
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

# Создаем тестовое приложение
def create_test_application():
    # Импортируем здесь, чтобы избежать циклического импорта
    from fastapi import Depends, FastAPI
    from sqlalchemy.orm import Session
    
    # Создаем тестовое приложение
    app = FastAPI()
    
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
    
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(auth_router.router, prefix="/auth")
    
    return app

# Создаем тестовое приложение
app = create_test_application()

# Создаем таблицы в тестовой базе данных
@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Фикстура для создания и удаления тестовой базы данных."""
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    yield  # Тесты выполняются здесь
    
    # Закрываем все соединения с базой данных
    from sqlalchemy import event
    from sqlalchemy.pool import NullPool
    
    # Принудительно закрываем все соединения
    engine.dispose()
    
    # Удаляем таблицы
    Base.metadata.drop_all(bind=engine)
    
    # Пытаемся удалить файл базы данных, если он существует
    db_path = "test.db"
    if os.path.exists(db_path):
        try:
            # Пытаемся удалить файл
            os.unlink(db_path)
        except PermissionError:
            # Игнорируем ошибки доступа, если файл заблокирован
            pass

# Фикстура для тестового клиента
@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

# Фикстура для сессии базы данных
@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

# Фикстура для тестового пользователя
@pytest.fixture(scope="function")
def test_user(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user

# Fixture for test user
@pytest.fixture(scope="function")
def test_user(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user
