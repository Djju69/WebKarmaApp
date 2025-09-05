"""
Tests for Two-Factor Authentication (2FA) endpoints.
"""
import pytest
from fastapi import status, Depends, Request
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json
from jose import jwt
import pyotp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, oauth2_scheme, get_current_user
from app.db.base import Base, get_db
from app.models.user import User
# Backup codes are stored in the User model
from app.schemas.two_factor import TwoFactorSetupResponse, TwoFactorVerifyRequest, TwoFactorEnableRequest, TwoFactorBackupCodesResponse
from app.main import app
from app.models.user import User, Role

# Create a test database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create test client
client = TestClient(app)

# Dependency to override get_db in tests
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# Fixture to set up and tear down the database for each test
@pytest.fixture(scope="function")
def db_session():
    # Create the database and tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session for testing
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Begin a nested transaction (using SAVEPOINT)
    nested = connection.begin_nested()
    
    # If the application code calls session.commit, it will end the nested
    # transaction. We need to start a new one when that happens.
    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    yield session
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()
    
    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)

# Test data
TEST_USER = {
    "username": "admin",
    "email": "admin@example.com",
    "password": "adminpass",
    "is_active": True,
    "is_verified": True,
    "is_2fa_enabled": False,
    "totp_secret": None,
    "backup_codes": []
}

# Fixture for creating a test user
@pytest.fixture
def test_user(db_session):
    from app.core.security import get_password_hash
    from app.models.user import User, Role
    
    # Create admin role if not exists
    admin_role = db_session.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrator role")
        db_session.add(admin_role)
        db_session.commit()
    
    # Create test user
    user_data = TEST_USER.copy()
    user = db_session.query(User).filter(User.email == user_data["email"]).first()
    
    if not user:
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
        user = User(**user_data)
        user.roles = [admin_role]
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    
    return user

# Fixture for creating an access token for the test user
@pytest.fixture
def user_token(test_user):
    from datetime import datetime, timedelta
    from jose import jwt
    from app.core.config import settings
    
    token_data = {
        "sub": test_user.username,
        "email": test_user.email,
        "is_2fa_verified": True,
        "jti": "test_jti_123",
        "scope": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    
    return jwt.encode(
        token_data,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

# Fixture for authenticated client
@pytest.fixture
def auth_client(test_client, user_token):
    test_client.headers.update({"Authorization": f"Bearer {user_token}"})
    return test_client

class Test2FASetup:
    """Tests for 2FA setup endpoint."""
    
    def test_setup_2fa_success(self, auth_client, test_user, db_session):
        """Test successful 2FA setup."""
        # First, ensure 2FA is disabled
        test_user.is_2fa_enabled = False
        test_user.totp_secret = None
        test_user.backup_codes = []
        db_session.add(test_user)
        db_session.commit()
        
        # Test 2FA setup
        response = auth_client.post("/2fa/setup")
        assert response.status_code == status.HTTP_200_OK, f"Unexpected status code: {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "qr_code_url" in data, "Response missing qr_code_url"
        assert "secret_key" in data, "Response missing secret_key"
        assert "backup_codes" in data, "Response missing backup_codes"
        assert len(data["backup_codes"]) > 0, "No backup codes were generated"
        
        # Verify user was updated in the database
        db_session.refresh(test_user)
        assert test_user.totp_secret is not None, "TOTP secret was not saved to the database"
        assert len(test_user.backup_codes) > 0, "Backup codes were not saved to the database"
    
    def test_setup_2fa_already_enabled(self, auth_client, test_user, db_session):
        """Test setup when 2FA is already enabled."""
        # Enable 2FA for the test user
        test_user.is_2fa_enabled = True
        test_user.totp_secret = "SECRET123"
        db_session.add(test_user)
        db_session.commit()
        
        # Make the request
        response = auth_client.post("/2fa/setup")
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {response.status_code}"
        assert "2FA already enabled" in response.text or "2FA уже включена" in response.text, \
            f"Unexpected error message: {response.text}"

class Test2FAEnable:
    """Tests for enabling 2FA."""
    
    def test_verify_2fa_success(self, auth_client, test_user, db_session):
        """Test successful 2FA verification."""
        # First, set up 2FA
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK, "2FA setup failed"
        
        secret_key = setup_response.json()["secret_key"]
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret_key)
        code = totp.now()
        
        # Verify the code
        response = auth_client.post("/2fa/verify", json={"code": code})
        assert response.status_code == status.HTTP_200_OK, f"2FA verification failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Response missing access_token"
        assert "token_type" in data, "Response missing token_type"
        
        # Verify user was updated in the database
        db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is True, "User's 2FA status was not updated to enabled"
    
    def test_enable_2fa_invalid_code(self, auth_client, test_user, db_session):
        """Test enable 2FA with an invalid code."""
        # First, setup 2FA to get the secret key
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK, "2FA setup failed"
        
        # Make the request with an invalid code
        response = auth_client.post(
            "/2fa/verify",
            json={"code": "123456"}  # Invalid code
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Expected 400, got {response.status_code}. Response: {response.text}"
        assert "Invalid 2FA code" in response.text or "Неверный код 2FA" in response.text, \
            f"Unexpected error message: {response.text}"

class Test2FADisable:
    """Tests for disabling 2FA."""
    
    def test_disable_2fa_not_enabled(self, auth_client, test_user):
        """Test disable 2FA when it's not enabled."""
        # Ensure 2FA is disabled
        test_user.is_2fa_enabled = False
        test_user.totp_secret = None
        test_user.backup_codes = []
        
        # Make the request when 2FA is not enabled
        response = auth_client.post("/2fa/disable")
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Expected 400, got {response.status_code}. Response: {response.text}"
        assert "2FA is not enabled" in response.text or "2FA не включена" in response.text, \
            f"Unexpected error message: {response.text}"

    def test_disable_2fa_success(self, auth_client, test_user, db_session):
        """Test successful 2FA disablement."""
        # Setup and enable 2FA for the test user
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK, "2FA setup failed"
        setup_data = setup_response.json()
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(setup_data["secret_key"])
        code = totp.now()
        
        # Verify the code to enable 2FA
        verify_response = auth_client.post("/2fa/verify", json={"code": code})
        assert verify_response.status_code == status.HTTP_200_OK, "2FA verification failed"
        
        # Now try to disable 2FA
        response = auth_client.post("/2fa/disable")
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        assert "2FA has been disabled" in response.text or "2FA отключена" in response.text, \
            f"Unexpected success message: {response.text}"
        
        # Verify user was updated in the database
        db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is False, "User's 2FA status was not updated to disabled"
        assert test_user.totp_secret is None, "TOTP secret was not cleared from the database"
        assert not test_user.backup_codes, "Backup codes were not cleared from the database"

    def test_disable_2fa_invalid_code(self, auth_client, test_user, db_session):
        """Test disable 2FA with an invalid code."""
        # Setup and enable 2FA for the test user
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        setup_data = setup_response.json()
        
        # Generate a valid TOTP code for setup
        totp = pyotp.TOTP(setup_data["secret_key"])
        valid_code = totp.now()
        
        # Enable 2FA with the valid code
        verify_response = auth_client.post("/2fa/verify", json={"code": valid_code})
        assert verify_response.status_code == status.HTTP_200_OK
        
        # Now try to disable 2FA with an invalid code
        response = auth_client.post("/2fa/disable", json={"code": "123456"})
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Expected 400, got {response.status_code}. Response: {response.text}"
        assert "Invalid 2FA code" in response.text or "Неверный код 2FA" in response.text, \
            f"Unexpected error message: {response.text}"

class Test2FABackupCodes:
    """Tests for 2FA backup codes."""
    
    def test_regenerate_backup_codes_success(self, auth_client, test_user, db_session):
        """Test successful regeneration of backup codes."""
        # Setup and enable 2FA for the test user
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        setup_data = setup_response.json()
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(setup_data["secret_key"])
        valid_code = totp.now()
        
        # Verify the code to enable 2FA
        verify_response = auth_client.post("/2fa/verify", json={"code": valid_code})
        assert verify_response.status_code == status.HTTP_200_OK
        
        # Get the current backup codes
        initial_backup_codes = setup_data["backup_codes"]
        
        # Regenerate backup codes
        response = auth_client.post("/2fa/regenerate-backup-codes")
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        
        # Verify the new backup codes are different from the initial ones
        assert data["backup_codes"] != initial_backup_codes
        
        # Verify the user was updated in the database
        db_session.refresh(test_user)
        assert len(test_user.backup_codes) > 0
    
    @pytest.mark.asyncio
    async def test_regenerate_backup_codes_missing_2fa(self, db_session):
        """Test regenerating backup codes without 2FA setup."""
        # Create a test user with 2FA disabled
        from app.models.user import User, Role
        from app.core.security import get_password_hash
        
        # Create test user data
        test_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": get_password_hash("testpass"),
            "is_active": True,
            "is_verified": True,
            "is_2fa_enabled": False,
            "totp_secret": None,
            "backup_codes": []
        }
        
        # Create and add user to database
        test_user = User(**test_user_data)
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Create a test client that bypasses authentication
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.endpoints import two_factor
        
        # Create a test app with the two_factor router
        app = FastAPI()
        app.include_router(two_factor.router)
        
        # Mock the get_current_active_user dependency
        async def override_get_current_active_user():
            return test_user
            
        # Override the dependency in the test app
        app.dependency_overrides[two_factor.get_current_active_user] = override_get_current_active_user
        
        # Create a test client with the test app
        test_client = TestClient(app)
        
        # Make the request to regenerate backup codes
        response = test_client.post(
            "/regenerate-backup-codes",
            headers={"Content-Type": "application/json"}
        )
        
        # Clean up the dependency override
        app.dependency_overrides = {}
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Expected 400, got {response.status_code}. Response: {response.text}"
        
        # Verify the error message
        data = response.json()
        assert "detail" in data, f"Expected 'detail' in response: {data}"
        assert data["detail"] == "2FA не включена для этого аккаунта", \
            f"Unexpected error message: {data['detail']}"
