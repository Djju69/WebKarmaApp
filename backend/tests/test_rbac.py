"""
Tests for role-based access control (RBAC).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.base import Base
from app.main import app
from app.models.user import User, Role, Permission
from app.tests.conftest import TestingSessionLocal

client = TestClient(app)

def test_admin_access(db: Session):
    """Test that admin can access admin-only endpoints."""
    # Create test admin user
    admin_role = Role(name="admin", description="Administrator")
    db.add(admin_role)
    
    test_admin = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password="hashedpassword",
        is_active=True,
        roles=[admin_role]
    )
    db.add(test_admin)
    db.commit()
    
    # Create access token
    access_token = create_access_token(subject=test_admin.id)
    
    # Test admin-only endpoint
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    
    # Cleanup
    db.delete(test_admin)
    db.delete(admin_role)
    db.commit()

def test_regular_user_access_denied(db: Session):
    """Test that regular user cannot access admin-only endpoints."""
    # Create test regular user
    user_role = Role(name="user", description="Regular user")
    db.add(user_role)
    
    test_user = User(
        email="user@example.com",
        username="regularuser",
        hashed_password="hashedpassword",
        is_active=True,
        roles=[user_role]
    )
    db.add(test_user)
    db.commit()
    
    # Create access token
    access_token = create_access_token(subject=test_user.id)
    
    # Test admin-only endpoint
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Should be 403 Forbidden
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]
    
    # Cleanup
    db.delete(test_user)
    db.delete(user_role)
    db.commit()

def test_permission_based_access(db: Session):
    """Test access control based on specific permissions."""
    # Create test permission and role
    view_users_perm = Permission(
        name="users:view",
        description="View users",
        module="users"
    )
    db.add(view_users_perm)
    
    manager_role = Role(
        name="manager",
        description="Manager",
        permissions=[view_users_perm]
    )
    db.add(manager_role)
    
    test_manager = User(
        email="manager@example.com",
        username="manager",
        hashed_password="hashedpassword",
        is_active=True,
        roles=[manager_role]
    )
    db.add(test_manager)
    db.commit()
    
    # Create access token
    access_token = create_access_token(subject=test_manager.id)
    
    # Test endpoint that requires users:view permission
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # Should be allowed because manager has users:view permission
    assert response.status_code == 200
    
    # Cleanup
    db.delete(test_manager)
    db.delete(manager_role)
    db.delete(view_users_perm)
    db.commit()
