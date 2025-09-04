"""
Tests for authentication endpoints.
"""
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token, 
    create_refresh_token,
    get_password_hash,
    verify_password
)
from app.db.base import Base
from app.main import app
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserInDB
from app.tests.conftest import TestingSessionLocal

client = TestClient(app)

# Test data
TEST_EMAIL = "test@example.com"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "TestPass123!"
TEST_FIRST_NAME = "Test"
TEST_LAST_NAME = "User"

def test_register_new_user(db: Session):
    """Test successful user registration."""
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewPass123!",
        "first_name": "New",
        "last_name": "User"
    }
    
    # Test registration
    with patch('app.core.security.send_verification_email') as mock_send_email:
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 201
        assert "id" in response.json()
        assert response.json()["email"] == user_data["email"]
        assert response.json()["username"] == user_data["username"]
        assert response.json()["first_name"] == user_data["first_name"]
        assert response.json()["last_name"] == user_data["last_name"]
        assert "hashed_password" not in response.json()
        
        # Verify email was sent
        mock_send_email.assert_called_once()
    
    # Cleanup
    db.query(User).filter(User.email == user_data["email"]).delete()
    db.commit()

def test_register_duplicate_email(db: Session):
    """Test registration with duplicate email."""
    # Create test user first
    test_user = User(
        email="duplicate@example.com",
        username="testuser1",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True
    )
    db.add(test_user)
    db.commit()
    
    # Try to register with same email
    user_data = {
        "email": "duplicate@example.com",
        "username": "differentuser",
        "password": "TestPass123!",
    }
    
    response = client.post("/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_login_success(db: Session):
    """Test successful user login."""
    # Create test user
    test_user = User(
        email=TEST_EMAIL,
        username=TEST_USERNAME,
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Test login
    response = client.post(
        "/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert "expires_in" in response.json()
    
    # Verify token can be used
    access_token = response.json()["access_token"]
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == TEST_EMAIL

    # Cleanup
    db.delete(test_user)
    db.commit()

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrong"}
    )
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_login_unverified_email(db: Session):
    """Test login with unverified email when verification is required."""
    if not settings.REQUIRE_EMAIL_VERIFICATION:
        pytest.skip("Email verification is not required in current settings")
    
    # Create unverified user
    test_user = User(
        email="unverified@example.com",
        username="unverified",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=False
    )
    db.add(test_user)
    db.commit()
    
    # Test login
    response = client.post(
        "/auth/login",
        data={"username": "unverified@example.com", "password": TEST_PASSWORD}
    )
    
    assert response.status_code == 403
    assert "Email not verified" in response.json()["detail"]
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_refresh_token(db: Session):
    """Test token refresh endpoint."""
    # Create test user
    test_user = User(
        email="refresh@example.com",
        username="refreshuser",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Create refresh token
    refresh_token = create_refresh_token(subject=test_user.id)
    
    # Test refresh
    response = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_logout(db: Session):
    """Test user logout."""
    # Create test user and token
    test_user = User(
        email="logout@example.com",
        username="logoutuser",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Create tokens
    access_token = create_access_token(subject=test_user.id)
    refresh_token = create_refresh_token(subject=test_user.id)
    
    # Test logout
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"
    
    # Verify tokens are blacklisted
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401  # Token should be invalid now
    
    # Cleanup
    db.delete(test_user)
    db.commit()

@pytest.mark.parametrize("user_data, expected_status, expected_detail", [
    ({"email": "test@example.com"}, 200, None),  # Email only
    ({"username": "testuser"}, 200, None),  # Username only
    ({"email": "test@example.com", "username": "testuser"}, 200, None),  # Both
    ({}, 422, None),  # Missing identifier
    ({"email": "nonexistent@example.com"}, 404, "User not found"),  # Non-existent email
    ({"username": "nonexistent"}, 404, "User not found"),  # Non-existent username
])
def test_get_user(db: Session, user_data, expected_status, expected_detail):
    """Test getting user by email or username."""
    # Create test user
    test_user = User(
        email=TEST_EMAIL,
        username=TEST_USERNAME,
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Test getting user
    response = client.get("/auth/user", params=user_data)
    
    assert response.status_code == expected_status
    if expected_status == 200:
        if "email" in user_data and user_data["email"]:
            assert response.json()["email"] == user_data["email"]
        if "username" in user_data and user_data["username"]:
            assert response.json()["username"] == user_data["username"]
    elif expected_detail:
        assert expected_detail in response.json()["detail"]
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_password_reset_flow(db: Session):
    """Test the complete password reset flow."""
    # Create test user
    test_user = User(
        email="reset@example.com",
        username="resetuser",
        hashed_password=get_password_hash("OldPass123!"),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Step 1: Request password reset
    with patch('app.core.security.send_password_reset_email') as mock_send_email:
        response = client.post(
            "/auth/forgot-password",
            json={"email": "reset@example.com"}
        )
        assert response.status_code == 200
        assert "Password reset email has been sent" in response.json()["message"]
        mock_send_email.assert_called_once()
    
    # Step 2: Get reset token (in a real app, this would come from the email)
    reset_token = create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES),
        token_type="reset"
    )
    
    # Step 3: Reset password
    new_password = "NewSecurePass123!"
    response = client.post(
        "/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": new_password,
            "confirm_password": new_password
        }
    )
    
    assert response.status_code == 200
    assert "Password updated successfully" in response.json()["message"]
    
    # Verify new password works
    db.refresh(test_user)
    assert verify_password(new_password, test_user.hashed_password)
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_get_current_user_invalid_token():
    """Test getting current user with invalid token."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_verify_email(db: Session):
    """Test email verification."""
    if not settings.REQUIRE_EMAIL_VERIFICATION:
        pytest.skip("Email verification is not required in current settings")
    
    # Create unverified user
    test_user = User(
        email="verify@example.com",
        username="verifyuser",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=False
    )
    db.add(test_user)
    db.commit()
    
    # Create verification token
    verify_token = create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(minutes=settings.EMAIL_TOKEN_EXPIRE_MINUTES),
        token_type="verify"
    )
    
    # Verify email
    response = client.post(
        "/auth/verify-email",
        json={"token": verify_token}
    )
    
    assert response.status_code == 200
    assert "Email verified successfully" in response.json()["message"]
    
    # Verify user is now verified
    db.refresh(test_user)
    assert test_user.is_verified is True
    
    # Cleanup
    db.delete(test_user)
    db.commit()

def test_rate_limiting(db: Session):
    """Test rate limiting on authentication endpoints."""
    # Create test user
    test_user = User(
        email="rate@example.com",
        username="rateuser",
        hashed_password=get_password_hash(TEST_PASSWORD),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()
    
    # Exceed rate limit
    for _ in range(settings.RATE_LIMIT_REQUESTS + 2):
        response = client.post(
            "/auth/login",
            data={"username": "rate@example.com", "password": "wrongpassword"}
        )
    
    # Should be rate limited
    assert response.status_code == 429
    assert "Too Many Requests" in response.json()["detail"]
    
    # Cleanup
    db.delete(test_user)
    db.commit()
