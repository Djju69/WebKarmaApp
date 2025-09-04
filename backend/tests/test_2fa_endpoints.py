"""
Tests for Two-Factor Authentication (2FA) endpoints.
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pyotp

from app.main import app
from app.models.user import User
from app.schemas.two_factor import TwoFactorSetupResponse, TwoFactorBackupCodesResponse
from app.core.security import create_access_token, get_password_hash

client = TestClient(app)

# Test data
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123",
    "is_active": True,
    "is_2fa_enabled": False,
    "totp_secret": None,
    "backup_codes": []
}

# Fixture for creating a test user
@pytest.fixture
def test_user(db_session):
    user_data = TEST_USER.copy()
    user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

# Fixture for creating an access token for the test user
@pytest.fixture
def user_token(test_user):
    return create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=15),
        is_2fa_verified=True,
        jti="test_jti_123",
        scope="access"
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
        # Make the request to setup 2FA
        response = auth_client.post("/2fa/setup")
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "qr_code_url" in data
        assert "secret_key" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        
        # Verify the user was updated in the database
        db_session.refresh(test_user)
        assert test_user.totp_secret is not None
        assert len(test_user.backup_codes) > 0
    
    def test_setup_2fa_already_enabled(self, auth_client, test_user, db_session):
        """Test setup when 2FA is already enabled."""
        # Enable 2FA for the test user
        test_user.is_2fa_enabled = True
        test_user.totp_secret = "SECRET123"
        db_session.commit()
        
        # Make the request
        response = auth_client.post("/2fa/setup")
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "2FA already enabled" in response.text or "2FA уже включена" in response.text

class Test2FAEnable:
    """Tests for enabling 2FA."""
    
    def test_enable_2fa_success(self, auth_client, test_user, db_session):
        """Test successful 2FA enablement."""
        # First, setup 2FA to get the secret key
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        setup_data = setup_response.json()
        secret_key = setup_data["secret_key"]
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret_key)
        valid_code = totp.now()
        
        # Make the request with a valid code
        response = auth_client.post(
            "/2fa/enable",
            json={"code": valid_code}
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the user was updated in the database
        db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is True
    
    def test_enable_2fa_invalid_code(self, auth_client, test_user, db_session):
        """Test enable 2FA with an invalid code."""
        # First, setup 2FA to get the secret key
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        
        # Make the request with an invalid code
        response = auth_client.post(
            "/2fa/enable",
            json={"code": "123456"}  # Invalid code
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

class Test2FADisable:
    """Tests for disabling 2FA."""
    
    def test_disable_2fa_success(self, auth_client, test_user, db_session):
        """Test successful 2FA disablement."""
        # Setup and enable 2FA for the test user
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        setup_data = setup_response.json()
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(setup_data["secret_key"])
        valid_code = totp.now()
        
        # Enable 2FA
        enable_response = auth_client.post(
            "/2fa/enable",
            json={"code": valid_code}
        )
        assert enable_response.status_code == status.HTTP_200_OK
        
        # Now disable 2FA
        disable_response = auth_client.post(
            "/2fa/disable",
            json={"code": valid_code}
        )
        
        # Assert the response
        assert disable_response.status_code == status.HTTP_200_OK
        
        # Verify the user was updated in the database
        db_session.refresh(test_user)
        assert test_user.is_2fa_enabled is False
        assert test_user.totp_secret is None
    
    def test_disable_2fa_invalid_code(self, auth_client, test_user, db_session):
        """Test disable 2FA with an invalid code."""
        # Setup and enable 2FA for the test user
        setup_response = auth_client.post("/2fa/setup")
        assert setup_response.status_code == status.HTTP_200_OK
        setup_data = setup_response.json()
        
        # Generate a valid TOTP code for setup
        totp = pyotp.TOTP(setup_data["secret_key"])
        valid_code = totp.now()
        
        # Enable 2FA
        enable_response = auth_client.post(
            "/2fa/enable",
            json={"code": valid_code}
        )
        assert enable_response.status_code == status.HTTP_200_OK
        
        # Try to disable with an invalid code
        response = auth_client.post(
            "/2fa/disable",
            json={"code": "123456"}  # Invalid code
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST

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
        
        # Enable 2FA
        enable_response = auth_client.post(
            "/2fa/enable",
            json={"code": valid_code}
        )
        assert enable_response.status_code == status.HTTP_200_OK
        
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
    async def test_regenerate_backup_codes_missing_2fa(self, test_client, test_user, db_session, monkeypatch):
        """Test regenerating backup codes without 2FA setup."""
        # Create a mock Redis client
        class MockRedis:
            async def get(self, key):
                return None
                
            async def set(self, key, value, ex=None):
                return True
                
            async def exists(self, key):
                return 0
                
            async def delete(self, key):
                return 1
                
            def __getattr__(self, name):
                # Handle any unimplemented async methods
                async def method(*args, **kwargs):
                    return None
                return method
        
        # Create a mock Redis instance
        mock_redis = MockRedis()
        
        # Mock the Redis manager
        class MockRedisManager:
            _instance = None
            _redis = mock_redis
            
            def __new__(cls):
                if cls._instance is None:
                    cls._instance = super(MockRedisManager, cls).__new__(cls)
                return cls._instance
                
            async def get_redis(self):
                return self._redis
                
            async def init_redis_cache(self):
                return self._redis
                
            async def close(self):
                pass
        
        # Replace the redis_manager with our mock
        from app.core import redis as redis_module
        monkeypatch.setattr(redis_module, 'redis_manager', MockRedisManager())
        
        # Also patch the get_redis dependency
        from app.core.deps import get_redis
        
        async def mock_get_redis():
            return mock_redis
            
        monkeypatch.setattr('app.core.redis.get_redis', mock_get_redis)
        
        # Create a valid token for the test user
        from app.core.security import create_access_token
        token = create_access_token(
            data={"sub": test_user.username},
            expires_delta=timedelta(minutes=15),
            is_2fa_verified=True,
            jti="test_jti_123",
            scope="access"
        )
        
        # Ensure test user has the required attributes
        test_user.is_2fa_enabled = False
        test_user.totp_secret = None
        test_user.backup_codes = []
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Make the request with the authenticated client
        headers = {"Authorization": f"Bearer {token}"}
        response = test_client.post("/2fa/regenerate-backup-codes", headers=headers)
        
        # Debug output
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "2FA не включена для этого аккаунта" in response.text
