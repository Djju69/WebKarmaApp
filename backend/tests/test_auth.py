"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.base import Base
from app.main import app
from app.models.user import User, Role
from app.tests.conftest import TestingSessionLocal

client = TestClient(app)

def test_login_success(db: Session):
    """Test successful user login."""
    # Create test user
    test_user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True
    )
    db.add(test_user)
    db.commit()
    
    # Test login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "secret"}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"

    # Cleanup
    db.delete(test_user)
    db.commit()

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrong"}
    )
    
    assert response.status_code == 400
    assert "Incorrect email or password" in response.json()["detail"]

def test_get_current_user(db: Session):
    """Test getting current user with valid token."""
    # Create test user
    test_user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password="hashedpassword",
        is_active=True
    )
    db.add(test_user)
    db.commit()
    
    # Create access token
    access_token = create_access_token(subject=test_user.id)
    
    # Test getting current user
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["email"] == "test2@example.com"
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_get_current_user_invalid_token():
    """Test getting current user with invalid token."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]
