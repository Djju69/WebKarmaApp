"""
Tests for roles and permissions endpoints.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi import Depends

# Import test app and fixtures from conftest
from conftest import app, test_client, test_user, test_permissions, test_role, override_get_db

# Import models and security
from app.models.user import User, Role, Permission, user_roles, role_permissions
from app.db.base import get_db, Base, SessionLocal
from app.core.config import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

# Create test client
client = TestClient(app)

# Override the get_current_user dependency for testing
app.dependency_overrides[get_current_user] = lambda: test_user

# Test user data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpass"

# Override the get_db dependency for testing
async def override_get_db():
    """Override the get_db dependency for testing."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the get_current_user dependency for testing
async def override_get_current_user():
    """Override the get_current_user dependency for testing."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
        if not user:
            user = create_test_user(
                db=db,
                email=TEST_USER_EMAIL,
                username="testuser",
                password=TEST_USER_PASSWORD,
                is_admin=True
            )
        return user
    finally:
        db.close()

# Override the RBAC.has_permission dependency for testing
async def override_has_permission(permissions, require_all=True):
    """Override the RBAC.has_permission dependency for testing."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Mock the get_current_user dependency
async def override_get_current_user():
    return User(
        id=1,
        email=TEST_USER_EMAIL,
        username="testuser",
        hashed_password=get_password_hash(TEST_USER_PASSWORD),
        is_active=True,
        is_verified=True
    )

# Override the get_current_user dependency in the test app
app.dependency_overrides[get_current_user] = override_get_current_user

def get_test_token(email: str) -> str:
    """Generate a test JWT token."""
    from datetime import datetime, timedelta
    import jwt
    
    token_data = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return create_access_token(token_data)

def create_test_user(db: Session, email: str, username: str, password: str, is_admin: bool = False) -> User:
    """Helper function to create a test user with admin role and permissions."""
    from app.models.user import Role, Permission, UserRole
    from app.models.user import user_roles, role_permissions
    
    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
        
    # Create user
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # If admin flag is set, add admin role with all permissions
    if is_admin:
        # Get or create admin role
        admin_role = db.query(Role).filter(Role.name == UserRole.ADMIN).first()
        if not admin_role:
            admin_role = Role(
                name=UserRole.ADMIN,
                description="Administrator role with full access",
                is_system=True
            )
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        
        # Add all required permissions to admin role
        required_permissions = [
            "role:create", "role:read", "role:update", "role:delete",
            "permission:read", "user:read", "user:update", "user:delete"
        ]
        
        for perm_name in required_permissions:
            permission = db.query(Permission).filter(Permission.name == perm_name).first()
            if not permission:
                permission = Permission(
                    name=perm_name,
                    description=f"Permission for {perm_name}",
                    module=perm_name.split(":")[0]
                )
                db.add(permission)
                db.commit()
                db.refresh(permission)
            
            if permission not in admin_role.permissions:
                admin_role.permissions.append(permission)
        
        db.commit()
        
        # Assign admin role to user if not already assigned
        if admin_role not in user.roles:
            user.roles.append(admin_role)
            db.commit()
    
    db.refresh(user)
    return user

def create_test_role(db: Session, name: str, description: str = None, is_system: bool = False) -> Role:
    """Helper function to create a test role."""
    # Check if role already exists
    role = db.query(Role).filter(Role.name == name).first()
    if role:
        return role
        
    role = Role(name=name, description=description, is_system=is_system)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

def create_test_permission(db: Session, name: str, description: str = None, module: str = "test") -> Permission:
    """Helper function to create a test permission."""
    # Check if permission already exists
    permission = db.query(Permission).filter(Permission.name == name).first()
    if permission:
        return permission
        
    permission = Permission(name=name, description=description, module=module)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission

def assign_role_to_user(db: Session, user_id: int, role_id: int):
    """Helper function to assign a role to a user."""
    # Check if the role is already assigned
    stmt = text("""
        SELECT 1 FROM user_roles 
        WHERE user_id = :user_id AND role_id = :role_id
    """)
    result = db.execute(stmt, {"user_id": user_id, "role_id": role_id}).scalar()
    
    if not result:
        stmt = text("""
            INSERT INTO user_roles (user_id, role_id) 
            VALUES (:user_id, :role_id)
        """)
        db.execute(stmt, {"user_id": user_id, "role_id": role_id})
        db.commit()

def assign_permission_to_role(db: Session, role_id: int, permission_id: int):
    """Helper function to assign a permission to a role."""
    # Check if the assignment already exists
    stmt = select(role_permissions).where(
        role_permissions.c.role_id == role_id,
        role_permissions.c.permission_id == permission_id
    )
    result = db.execute(stmt).first()
    if not result:
        stmt = insert(role_permissions).values(
            role_id=role_id,
            permission_id=permission_id
        )
        db.execute(stmt)
        db.commit()

# Helper function to ensure test permissions exist
def ensure_test_permissions(db: Session):
    """Helper function to ensure test permissions exist in the database."""
    # Define test permissions
    test_permissions = [
        {"name": "test:read", "description": "Test read permission", "module": "test"},
        {"name": "test:write", "description": "Test write permission", "module": "test"},
        {"name": "test:delete", "description": "Test delete permission", "module": "test"},
    ]
    
    # Create permissions if they don't exist
    permissions = {}
    for perm_data in test_permissions:
        permission = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not permission:
            permission = Permission(**perm_data)
            db.add(permission)
            db.commit()
            db.refresh(permission)
        
        # Add to permissions dict whether it's new or existing
        permissions[perm_data["name"]] = permission
    
    return permissions

def get_auth_headers(email: str, password: str):
    """Helper function to get authentication headers."""
    # For testing purposes, we'll use a simple JWT token with the user's email
    from datetime import datetime, timedelta
    import jwt
    from app.core.config import settings
    
    # Create a simple JWT token
    token_data = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

def get_test_token(user_email: str) -> str:
    """Generate a test JWT token for the given user email."""
    from datetime import datetime, timedelta
    import jwt
    from app.core.config import settings
    
    token_data = {
        "sub": user_email,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def test_create_role(test_client, test_user, test_permissions, db_session):
    """Test creating a new role using the API."""
    # Get the test user and ensure it has the required permissions
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator role")
        admin_user.roles.append(admin_role)
    
    # Add required permissions to the admin role
    admin_role.permissions = [
        test_permissions["role:create"],
        test_permissions["role:read"],
        test_permissions["permission:read"]
    ]
    db_session.add(admin_role)
    db_session.commit()
    
    # Create an access token for the test user
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Prepare test data
    role_data = {
        "name": "test_role_new",
        "description": "New test role created via API",
        "permission_ids": [test_permissions["test:read"].id, test_permissions["test:write"].id]
    }
    
    # Make the API request
    response = test_client.post(
        "/api/roles/",
        json=role_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Verify the response
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    assert result["name"] == role_data["name"]
    assert result["description"] == role_data["description"]
    assert len(result["permissions"]) == 2
    
    # Verify the role was created in the database
    db_role = db_session.query(Role).filter(Role.name == role_data["name"]).first()
    assert db_role is not None
    assert db_role.name == role_data["name"]
    assert db_role.description == role_data["description"]
    assert len(db_role.permissions) == 2
    assert {p.name for p in db_role.permissions} == {"test:read", "test:write"}
    assert {p.name for p in db_role.permissions} == {"test:read", "test:write"}

def test_get_role(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование получения роли по ID через API."""
    # Получаем тестового пользователя и настраиваем необходимые права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator role")
        admin_user.roles.append(admin_role)
    
    # Добавляем необходимые права доступа
    admin_role.permissions = [test_permissions["role:read"]]
    db_session.add(admin_role)
    db_session.commit()
    
    # Создаем access token для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Выполняем запрос к API
    response = test_client.get(
        f"/api/roles/{test_role.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["id"] == test_role.id
    assert result["name"] == test_role.name
    assert result["description"] == test_role.description

def test_update_role(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование обновления роли через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [
        test_permissions["role:update"],
        test_permissions["role:read"],
    ]
    db_session.add(admin_role)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Подготавливаем данные для обновления
    update_data = {
        "name": "обновленная_роль",
        "description": "Обновленное описание роли",
        "permission_ids": [test_permissions["test:write"].id, test_permissions["test:delete"].id]
    }
    
    # Выполняем запрос на обновление
    response = test_client.put(
        f"/api/roles/{test_role.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["name"] == update_data["name"]
    assert result["description"] == update_data["description"]
    assert len(result["permissions"]) == 2
    
    # Проверяем, что данные обновились в базе
    db_role = db_session.query(Role).filter(Role.id == test_role.id).first()
    assert db_role is not None
    assert db_role.name == update_data["name"]
    assert db_role.description == update_data["description"]
    assert len(db_role.permissions) == 2
    assert {p.name for p in db_role.permissions} == {"test:write", "test:delete"}

def test_delete_role(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование удаления роли через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [test_permissions["role:delete"]]
    db_session.add(admin_role)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Сохраняем ID роли перед удалением
    role_id = test_role.id
    
    # Выполняем запрос на удаление
    response = test_client.delete(
        f"/api/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ (204 No Content)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем, что роль удалена из базы
    db_role = db_session.query(Role).filter(Role.id == role_id).first()
    assert db_role is None

def test_search_roles(test_client, test_user, test_permissions, db_session):
    """Тестирование поиска ролей по имени и описанию."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [test_permissions["role:read"]]
    db_session.add(admin_role)
    
    # Создаем тестовые роли для поиска
    test_roles = [
        ("manager", "Менеджер проекта", "Руководит проектом"),
        ("developer", "Разработчик", "Пишет код"),
        ("tester", "Тестировщик", "Тестирует приложение"),
        ("devops", "DevOps инженер", "Настраивает инфраструктуру"),
        ("analyst", "Аналитик", "Анализирует требования")
    ]
    
    for name, display_name, description in test_roles:
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            is_system=False
        )
        db_session.add(role)
    
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Тестируем поиск по частичному совпадению имени
    response = test_client.get(
        "/api/roles/search",
        params={"q": "dev"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result) >= 2  # developer и devops
    assert any(r["name"] == "developer" for r in result)
    assert any(r["name"] == "devops" for r in result)
    
    # Тестируем поиск по отображаемому имени
    response = test_client.get(
        "/api/roles/search",
        params={"q": "инженер"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result) == 1
    assert result[0]["name"] == "devops"
    
    # Тестируем поиск по описанию
    response = test_client.get(
        "/api/roles/search",
        params={"q": "требования"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result) == 1
    assert result[0]["name"] == "analyst"
    
    # Тестируем поиск с пустым запросом (должен вернуть все роли)
    response = test_client.get(
        "/api/roles/search",
        params={"q": ""},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result) >= len(test_roles)  # Как минимум столько, сколько мы создали


def test_remove_permissions_from_role(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование удаления разрешений у роли через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [
        test_permissions["role:update"],
        test_permissions["permission:read"]
    ]
    db_session.add(admin_role)
    
    # Назначаем тестовые разрешения роли
    test_role.permissions = [
        test_permissions["test:read"],
        test_permissions["test:write"],
        test_permissions["test:delete"]
    ]
    db_session.add(test_role)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Подготавливаем данные для запроса (удаляем два разрешения)
    permission_ids_to_remove = [
        test_permissions["test:read"].id,
        test_permissions["test:write"].id
    ]
    
    # Выполняем запрос на удаление разрешений
    response = test_client.request(
        "DELETE",
        f"/api/roles/{test_role.id}/permissions",
        json={"permission_ids": permission_ids_to_remove},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что осталось только одно разрешение
    assert len(result["permissions"]) == 1
    remaining_permission_ids = {p["id"] for p in result["permissions"]}
    assert test_permissions["test:delete"].id in remaining_permission_ids
    
    # Проверяем, что изменения сохранились в базе
    db_role = db_session.query(Role).filter(Role.id == test_role.id).first()
    assert db_role is not None
    assert len(db_role.permissions) == 1
    assert db_role.permissions[0].id == test_permissions["test:delete"].id
    
    # Проверяем, что можно удалить все разрешения
    response = test_client.request(
        "DELETE",
        f"/api/roles/{test_role.id}/permissions",
        json={"permission_ids": [test_permissions["test:delete"].id]},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["permissions"]) == 0


def test_assign_permissions_to_role(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование назначения разрешений роли через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [
        test_permissions["role:update"],
        test_permissions["permission:read"]
    ]
    db_session.add(admin_role)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Подготавливаем данные для запроса
    permission_ids = [
        test_permissions["test:read"].id,
        test_permissions["test:write"].id
    ]
    
    # Выполняем запрос на назначение разрешений
    response = test_client.post(
        f"/api/roles/{test_role.id}/permissions",
        json={"permission_ids": permission_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что роль содержит назначенные разрешения
    assert len(result["permissions"]) == 2
    assigned_permission_ids = {p["id"] for p in result["permissions"]}
    assert set(permission_ids).issubset(assigned_permission_ids)
    
    # Проверяем, что разрешения сохранились в базе
    db_role = db_session.query(Role).filter(Role.id == test_role.id).first()
    assert db_role is not None
    assert len(db_role.permissions) == 2
    assert {p.id for p in db_role.permissions} == set(permission_ids)
    
    # Проверяем, что нельзя назначить несуществующие разрешения
    invalid_permission_ids = [999999]  # Несуществующий ID
    response = test_client.post(
        f"/api/roles/{test_role.id}/permissions",
        json={"permission_ids": invalid_permission_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_resource_based_access_control(test_client, test_user, test_permissions, db_session):
    """Тестирование доступа к ресурсам на основе ролей."""
    # Создаем тестовые роли
    from app.models.user import User, Role, Permission
    
    # 1. Роль владельца документа
    owner_role = Role(
        name="document_owner",
        description="Владелец документа",
        is_system=False
    )
    
    # 2. Роль редактора документа
    editor_role = Role(
        name="document_editor",
        description="Редактор документа",
        is_system=False
    )
    
    # 3. Роль читателя документа
    reader_role = Role(
        name="document_reader",
        description="Читатель документа",
        is_system=False
    )
    
    # Создаем разрешения
    view_doc_perm = Permission(name="document:view", description="Просмотр документа")
    edit_doc_perm = Permission(name="document:edit", description="Редактирование документа")
    delete_doc_perm = Permission(name="document:delete", description="Удаление документа")
    share_doc_perm = Permission(name="document:share", description="Предоставление доступа к документу")
    
    # Назначаем разрешения ролям
    owner_role.permissions = [view_doc_perm, edit_doc_perm, delete_doc_perm, share_doc_perm]
    editor_role.permissions = [view_doc_perm, edit_doc_perm]
    reader_role.permissions = [view_doc_perm]
    
    # Создаем тестовых пользователей
    owner = User(
        email="owner@example.com",
        username="owner",
        hashed_password="hashed_password",
        is_active=True,
        roles=[owner_role]
    )
    
    editor = User(
        email="editor@example.com",
        username="editor",
        hashed_password="hashed_password",
        is_active=True,
        roles=[editor_role]
    )
    
    reader = User(
        email="reader@example.com",
        username="reader",
        hashed_password="hashed_password",
        is_active=True,
        roles=[reader_role]
    )
    
    # Создаем тестовый документ
    from app.models.document import Document
    test_doc = Document(
        title="Тестовый документ",
        content="Содержимое тестового документа",
        owner_id=owner.id
    )
    
    # Сохраняем все в базу
    db_session.add_all([
        owner_role, editor_role, reader_role,
        view_doc_perm, edit_doc_perm, delete_doc_perm, share_doc_perm,
        owner, editor, reader, test_doc
    ])
    db_session.commit()
    
    # Создаем токены доступа
    from app.core.security import create_access_token
    owner_token = create_access_token(data={"sub": str(owner.id)})
    editor_token = create_access_token(data={"sub": str(editor.id)})
    reader_token = create_access_token(data={"sub": str(reader.id)})
    
    # Вспомогательная функция для проверки доступа к документу
    def check_document_access(token, method, expected_status):
        url = f"/api/documents/{test_doc.id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        if method == "GET":
            response = test_client.get(url, headers=headers)
        elif method == "PUT":
            response = test_client.put(url, json={"title": "Обновленный заголовок"}, headers=headers)
        elif method == "DELETE":
            response = test_client.delete(url, headers=headers)
        elif method == "SHARE":
            response = test_client.post(
                f"{url}/share",
                json={"user_id": 2, "role": "reader"},
                headers=headers
            )
        
        return response.status_code == expected_status
    
    # Проверяем доступ к документам
    
    # 1. Владелец имеет полный доступ
    assert check_document_access(owner_token, "GET", status.HTTP_200_OK) is True
    assert check_document_access(owner_token, "PUT", status.HTTP_200_OK) is True
    assert check_document_access(owner_token, "DELETE", status.HTTP_204_NO_CONTENT) is True
    assert check_document_access(owner_token, "SHARE", status.HTTP_200_OK) is True
    
    # 2. Редактор может только просматривать и редактировать
    assert check_document_access(editor_token, "GET", status.HTTP_200_OK) is True
    assert check_document_access(editor_token, "PUT", status.HTTP_200_OK) is True
    assert check_document_access(editor_token, "DELETE", status.HTTP_403_FORBIDDEN) is True
    assert check_document_access(editor_token, "SHARE", status.HTTP_403_FORBIDDEN) is True
    
    # 3. Читатель может только просматривать
    assert check_document_access(reader_token, "GET", status.HTTP_200_OK) is True
    assert check_document_access(reader_token, "PUT", status.HTTP_403_FORBIDDEN) is True
    assert check_document_access(reader_token, "DELETE", status.HTTP_403_FORBIDDEN) is True
    assert check_document_access(reader_token, "SHARE", status.HTTP_403_FORBIDDEN) is True
    
    # 4. Проверяем доступ к несуществующему документу
    def check_nonexistent_document(token):
        response = test_client.get(
            "/api/documents/999999",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.status_code
    
    # Все должны получить 404 при попытке доступа к несуществующему документу
    assert check_nonexistent_document(owner_token) == status.HTTP_404_NOT_FOUND
    assert check_nonexistent_document(editor_token) == status.HTTP_404_NOT_FOUND
    assert check_nonexistent_document(reader_token) == status.HTTP_404_NOT_FOUND


def test_role_hierarchy(test_client, test_user, test_permissions, db_session):
    """Тестирование иерархии ролей и наследования разрешений."""
    # Создаем иерархию ролей
    # senior > manager > employee
    
    # 1. Создаем базовую роль (employee)
    employee_role = Role(
        name="employee",
        description="Сотрудник",
        is_system=False
    )
    employee_role.permissions = [
        test_permissions["document:view"],
        test_permissions["document:edit_own"]
    ]
    
    # 2. Создаем роль менеджера, которая наследует права employee
    manager_role = Role(
        name="manager",
        description="Менеджер",
        is_system=False
    )
    manager_role.permissions = [
        test_permissions["document:approve"],
        test_permissions["team:view"]
    ]
    
    # 3. Создаем старшую роль, которая наследует права manager
    senior_role = Role(
        name="senior_manager",
        description="Старший менеджер",
        is_system=False
    )
    senior_role.permissions = [
        test_permissions["document:delete"],
        test_permissions["team:manage"]
    ]
    
    # Настраиваем наследование ролей
    manager_role.parent = employee_role
    senior_role.parent = manager_role
    
    # Создаем пользователей с разными ролями
    from app.models.user import User
    
    employee_user = User(
        email="employee@example.com",
        username="employee",
        hashed_password="hashed_password",
        is_active=True,
        roles=[employee_role]
    )
    
    manager_user = User(
        email="manager@example.com",
        username="manager",
        hashed_password="hashed_password",
        is_active=True,
        roles=[manager_role]
    )
    
    senior_user = User(
        email="senior@example.com",
        username="senior_manager",
        hashed_password="hashed_password",
        is_active=True,
        roles=[senior_role]
    )
    
    db_session.add_all([employee_role, manager_role, senior_role, 
                       employee_user, manager_user, senior_user])
    db_session.commit()
    
    # Создаем токены доступа
    from app.core.security import create_access_token
    employee_token = create_access_token(data={"sub": str(employee_user.id)})
    manager_token = create_access_token(data={"sub": str(manager_user.id)})
    senior_token = create_access_token(data={"sub": str(senior_user.id)})
    
    # Вспомогательная функция для проверки разрешений
    def check_permission(token, permission):
        response = test_client.get(
            "/api/auth/check-permission",
            params={"permission": permission},
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.status_code == status.HTTP_200_OK and response.json()["has_permission"]
    
    # Проверяем наследование разрешений
    
    # 1. Базовые разрешения сотрудника
    assert check_permission(employee_token, "document:view") is True
    assert check_permission(employee_token, "document:edit_own") is True
    assert check_permission(employee_token, "document:approve") is False
    assert check_permission(employee_token, "document:delete") is False
    
    # 2. Менеджер наследует права сотрудника + свои
    assert check_permission(manager_token, "document:view") is True  # От employee
    assert check_permission(manager_token, "document:approve") is True  # Своё
    assert check_permission(manager_token, "team:view") is True  # Своё
    assert check_permission(manager_token, "document:delete") is False  # Только у senior
    
    # 3. Старший менеджер наследует все права
    assert check_permission(senior_token, "document:view") is True  # От employee
    assert check_permission(senior_token, "document:approve") is True  # От manager
    assert check_permission(senior_token, "document:delete") is True  # Своё
    assert check_permission(senior_token, "team:manage") is True  # Своё
    
    # Проверяем, что можно получить все унаследованные разрешения
    def get_user_permissions(token):
        response = test_client.get(
            "/api/auth/me/permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        return {p["name"] for p in response.json()["permissions"]}
    
    # Проверяем, что пользователь видит все унаследованные разрешения
    manager_perms = get_user_permissions(manager_token)
    assert "document:view" in manager_perms  # От employee
    assert "document:approve" in manager_perms  # Своё
    assert "team:view" in manager_perms  # Своё
    assert "document:delete" not in manager_perms  # Не должно быть доступно
    
    senior_perms = get_user_permissions(senior_token)
    assert "document:view" in senior_perms  # От employee
    assert "document:approve" in senior_perms  # От manager
    assert "document:delete" in senior_perms  # Своё
    assert "team:manage" in senior_perms  # Своё


def test_role_based_access_control(test_client, test_user, test_permissions, db_session):
    """Тестирование контроля доступа на основе ролей (RBAC)."""
    # Создаем тестовых пользователей с разными ролями
    from app.models.user import User
    
    # 1. Администратор (имеет все права)
    admin_user = test_user
    admin_role = Role(name="admin", description="Администратор")
    admin_role.permissions = list(test_permissions.values())  # Все права
    admin_user.roles = [admin_role]
    
    # 2. Менеджер контента (ограниченные права)
    content_manager = User(
        email="content.manager@example.com",
        username="content_manager",
        hashed_password="hashed_password",
        is_active=True
    )
    content_manager_role = Role(name="content_manager", description="Менеджер контента")
    content_manager_role.permissions = [
        test_permissions["content:create"],
        test_permissions["content:edit"],
        test_permissions["content:view"]
    ]
    content_manager.roles = [content_manager_role]
    
    # 3. Обычный пользователь (минимальные права)
    regular_user = User(
        email="user@example.com",
        username="regular_user",
        hashed_password="hashed_password",
        is_active=True
    )
    
    db_session.add_all([admin_user, content_manager, regular_user])
    db_session.commit()
    
    # Создаем токены доступа для пользователей
    from app.core.security import create_access_token
    admin_token = create_access_token(data={"sub": str(admin_user.id)})
    manager_token = create_access_token(data={"sub": str(content_manager.id)})
    user_token = create_access_token(data={"sub": str(regular_user.id)})
    
    # Тестируем доступ к защищенным эндпоинтам
    
    # 1. Доступ к созданию роли (требуется permission: role:create)
    role_data = {
        "name": "test_role",
        "description": "Test Role",
        "is_system": False
    }
    
    # Администратор должен иметь доступ
    response = test_client.post(
        "/api/roles/",
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    
    # Менеджер контента не должен иметь доступ
    response = test_client.post(
        "/api/roles/",
        json=role_data,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # 2. Доступ к созданию контента (требуется permission: content:create)
    content_data = {"title": "Test Content", "body": "Test body"}
    
    # И администратор, и менеджер контента должны иметь доступ
    for token in [admin_token, manager_token]:
        response = test_client.post(
            "/api/content/",
            json=content_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_201_CREATED
    
    # Обычный пользователь не должен иметь доступ
    response = test_client.post(
        "/api/content/",
        json=content_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # 3. Доступ к просмотру контента (требуется permission: content:view)
    # Все пользователи должны иметь доступ
    for token in [admin_token, manager_token, user_token]:
        response = test_client.get(
            "/api/content/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
    
    # 4. Доступ к управлению пользователями (требуется permission: user:manage)
    # Только администратор должен иметь доступ
    response = test_client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Менеджер контента не должен иметь доступ
    response = test_client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_check_user_permissions(test_client, test_user, test_permissions, db_session):
    """Тестирование проверки прав пользователя на основе его ролей."""
    # Настраиваем тестового пользователя
    test_user = test_user
    
    # Создаем тестовые роли с разными разрешениями
    role1 = Role(name="content_manager", description="Менеджер контента", is_system=False)
    role2 = Role(name="moderator", description="Модератор", is_system=False)
    
    # Назначаем разрешения ролям
    role1.permissions = [
        test_permissions["content:create"],
        test_permissions["content:edit"]
    ]
    
    role2.permissions = [
        test_permissions["content:moderate"],
        test_permissions["user:ban"]
    ]
    
    # Добавляем роли пользователю
    test_user.roles.extend([role1, role2])
    
    db_session.add_all([role1, role2, test_user])
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    
    # Тестируем проверку разрешений через API
    # Пользователь должен иметь разрешение content:create
    response = test_client.get(
        "/api/auth/check-permission",
        params={"permission": "content:create"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["has_permission"] is True
    
    # Пользователь должен иметь разрешение user:ban
    response = test_client.get(
        "/api/auth/check-permission",
        params={"permission": "user:ban"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["has_permission"] is True
    
    # Пользователь не должен иметь несуществующее разрешение
    response = test_client.get(
        "/api/auth/check-permission",
        params={"permission": "nonexistent:permission"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["has_permission"] is False
    
    # Проверяем, что неавторизованный пользователь не имеет доступа
    response = test_client.get(
        "/api/auth/check-permission",
        params={"permission": "content:create"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_remove_roles_from_user(test_client, test_user, test_permissions, db_session):
    """Тестирование удаления ролей у пользователя через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [
        test_permissions["user:update"],
        test_permissions["role:read"]
    ]
    db_session.add(admin_role)
    
    # Создаем тестового пользователя с ролями
    from app.models.user import User
    test_target_user = User(
        email="test_target@example.com",
        username="test_target",
        hashed_password="hashed_password",
        is_active=True
    )
    
    # Создаем роли для тестирования
    roles = []
    for i in range(1, 4):
        role = Role(
            name=f"test_role_{i}",
            description=f"Тестовая роль {i}",
            is_system=False
        )
        db_session.add(role)
        roles.append(role)
    
    # Назначаем роли пользователю
    test_target_user.roles = roles.copy()
    db_session.add(test_target_user)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Удаляем часть ролей (первые две)
    roles_to_remove = [roles[0].id, roles[1].id]
    
    # Выполняем запрос на удаление ролей
    response = test_client.request(
        "DELETE",
        f"/api/users/{test_target_user.id}/roles",
        json={"role_ids": roles_to_remove},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что роли удалены
    remaining_role_ids = {r["id"] for r in result["roles"]}
    assert roles[0].id not in remaining_role_ids
    assert roles[1].id not in remaining_role_ids
    assert roles[2].id in remaining_role_ids
    
    # Проверяем, что изменения сохранились в базе
    db_session.refresh(test_target_user)
    assert len(test_target_user.roles) == 1
    assert test_target_user.roles[0].id == roles[2].id
    
    # Пытаемся удалить несуществующую роль
    invalid_role_ids = [999999]
    response = test_client.request(
        "DELETE",
        f"/api/users/{test_target_user.id}/roles",
        json={"role_ids": invalid_role_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Должны получить успешный ответ, так как несуществующие роли игнорируются
    assert response.status_code == status.HTTP_200_OK
    
    # Проверяем, что роли пользователя не изменились
    db_session.refresh(test_target_user)
    assert len(test_target_user.roles) == 1


def test_assign_roles_to_user(test_client, test_user, test_role, test_permissions, db_session):
    """Тестирование назначения ролей пользователю через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [
        test_permissions["user:update"],
        test_permissions["role:read"]
    ]
    db_session.add(admin_role)
    
    # Создаем тестового пользователя, которому будем назначать роли
    from app.models.user import User
    test_target_user = User(
        email="test_target@example.com",
        username="test_target",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(test_target_user)
    
    # Создаем дополнительные роли для тестирования
    roles = []
    for i in range(1, 4):
        role = Role(
            name=f"test_role_{i}",
            description=f"Тестовая роль {i}",
            is_system=False
        )
        db_session.add(role)
        roles.append(role)
    
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Подготавливаем данные для запроса (назначаем роли)
    role_ids = [role.id for role in roles[:2]]  # Берем первые две роли
    
    # Выполняем запрос на назначение ролей
    response = test_client.post(
        f"/api/users/{test_target_user.id}/roles",
        json={"role_ids": role_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что пользователю назначены правильные роли
    assert len(result["roles"]) == len(role_ids)
    assigned_role_ids = {r["id"] for r in result["roles"]}
    assert set(role_ids).issubset(assigned_role_ids)
    
    # Проверяем, что роли сохранились в базе
    db_user = db_session.query(User).filter(User.id == test_target_user.id).first()
    assert db_user is not None
    assert len(db_user.roles) == len(role_ids)
    assert {r.id for r in db_user.roles} == set(role_ids)
    
    # Тестируем обновление ролей (добавляем третью роль)
    new_role_ids = [r.id for r in roles]  # Все три роли
    response = test_client.post(
        f"/api/users/{test_target_user.id}/roles",
        json={"role_ids": new_role_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["roles"]) == len(new_role_ids)
    
    # Проверяем, что нельзя назначить несуществующие роли
    invalid_role_ids = [999999]  # Несуществующий ID
    response = test_client.post(
        f"/api/users/{test_target_user.id}/roles",
        json={"role_ids": invalid_role_ids},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_filter_roles_by_system_status(test_client, test_user, test_permissions, db_session):
    """Тестирование фильтрации ролей по системному статусу."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [test_permissions["role:read"]]
    db_session.add(admin_role)
    
    # Создаем тестовые роли с разными статусами
    system_roles = [
        ("system_role_1", "Системная роль 1", True),
        ("system_role_2", "Системная роль 2", True)
    ]
    
    custom_roles = [
        ("custom_role_1", "Пользовательская роль 1", False),
        ("custom_role_2", "Пользовательская роль 2", False)
    ]
    
    for name, description, is_system in system_roles + custom_roles:
        role = Role(
            name=name,
            description=description,
            is_system=is_system
        )
        db_session.add(role)
    
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Тестируем фильтрацию системных ролей
    response = test_client.get(
        "/api/roles/",
        params={"is_system": "true"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что вернулись только системные роли
    system_role_names = {r[0] for r in system_roles}
    returned_role_names = {r["name"] for r in result["items"]}
    assert all(r["is_system"] for r in result["items"])
    assert system_role_names.issubset(returned_role_names)
    
    # Тестируем фильтрацию пользовательских ролей
    response = test_client.get(
        "/api/roles/",
        params={"is_system": "false"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что вернулись только пользовательские роли
    custom_role_names = {r[0] for r in custom_roles}
    returned_role_names = {r["name"] for r in result["items"]}
    assert all(not r["is_system"] for r in result["items"])
    assert custom_role_names.issubset(returned_role_names)


def test_list_roles(test_client, test_user, test_permissions, db_session):
    """Тестирование получения списка ролей с пагинацией через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [test_permissions["role:read"]]
    db_session.add(admin_role)
    
    # Создаем несколько тестовых ролей
    roles = []
    for i in range(1, 6):
        role = Role(
            name=f"test_role_{i}",
            description=f"Тестовая роль {i}",
            is_system=False
        )
        db_session.add(role)
        roles.append(role)
    
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Тестируем пагинацию
    # Первая страница (2 элемента)
    response = test_client.get(
        "/api/roles/",
        params={"skip": 0, "limit": 2},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["items"]) == 2
    assert result["total"] >= 5  # Минимум 5 ролей (новые + системные)
    assert result["skip"] == 0
    assert result["limit"] == 2
    
    # Проверяем, что ответ содержит правильные поля
    for role in result["items"]:
        assert "id" in role
        assert "name" in role
        assert "description" in role
        assert "is_system" in role
    
    # Вторая страница (следующие 2 элемента)
    response = test_client.get(
        "/api/roles/",
        params={"skip": 2, "limit": 2},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["items"]) == 2
    
    # Проверяем сортировку по умолчанию (по имени)
    names = [role["name"] for role in result["items"]]
    assert names == sorted(names)


def test_list_permissions(test_client, test_user, test_permissions, db_session):
    """Тестирование получения списка разрешений через API."""
    # Настраиваем тестового пользователя и его права
    admin_user = test_user
    admin_role = next((r for r in admin_user.roles if r.name == "admin"), None)
    if not admin_role:
        admin_role = Role(name="admin", description="Администратор")
        admin_user.roles.append(admin_role)
    
    # Настраиваем необходимые права доступа
    admin_role.permissions = [test_permissions["permission:read"]]
    db_session.add(admin_role)
    db_session.commit()
    
    # Создаем токен доступа для тестового пользователя
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(admin_user.id)})
    
    # Выполняем запрос к API
    response = test_client.get(
        "/api/roles/permissions/",
        params={"skip": 0, "limit": 100},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Проверяем ответ
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    
    # Проверяем, что в ответе есть все тестовые разрешения
    assert len(result) >= len(test_permissions)
    permission_names = {p["name"] for p in result}
    for perm_name in test_permissions.keys():
        assert perm_name in permission_names
