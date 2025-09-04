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
    
    # Create permissions if they don't exist
    created_permissions = {}
    for perm_data in permissions:
        permission = db_session.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not permission:
            permission = Permission(**perm_data)
            db_session.add(permission)
            db_session.commit()
            db_session.refresh(permission)
        created_permissions[perm_data["name"]] = permission
    
    yield created_permissions
    
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
