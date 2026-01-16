"""API endpoint tests"""

import pytest
from datetime import datetime, timezone

from myome.api.auth import (
    get_password_hash,
    verify_password,
    create_token_pair,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    TokenPair,
)
from myome.api.middleware.rate_limit import RateLimiter


class TestPasswordHashing:
    """Tests for password hashing"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_correct_password(self):
        """Test verifying correct password"""
        password = "securepassword456"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password"""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestTokens:
    """Tests for JWT token handling"""
    
    def test_create_access_token(self):
        """Test creating access token"""
        user_id = "test-user-123"
        token = create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
    
    def test_create_refresh_token(self):
        """Test creating refresh token"""
        user_id = "test-user-456"
        token = create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_create_token_pair(self):
        """Test creating token pair"""
        user_id = "test-user-789"
        tokens = create_token_pair(user_id)
        
        assert isinstance(tokens, TokenPair)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
    
    def test_verify_access_token(self):
        """Test verifying access token"""
        user_id = "verify-test-user"
        token = create_access_token(user_id)
        
        verified_id = verify_access_token(token)
        assert verified_id == user_id
    
    def test_verify_refresh_token(self):
        """Test verifying refresh token"""
        user_id = "refresh-test-user"
        token = create_refresh_token(user_id)
        
        verified_id = verify_refresh_token(token)
        assert verified_id == user_id
    
    def test_access_token_not_valid_as_refresh(self):
        """Test that access token cannot be used as refresh token"""
        from myome.core.exceptions import AuthenticationException
        
        user_id = "test-user"
        access_token = create_access_token(user_id)
        
        with pytest.raises(AuthenticationException):
            verify_refresh_token(access_token)
    
    def test_refresh_token_not_valid_as_access(self):
        """Test that refresh token cannot be used as access token"""
        from myome.core.exceptions import AuthenticationException
        
        user_id = "test-user"
        refresh_token = create_refresh_token(user_id)
        
        with pytest.raises(AuthenticationException):
            verify_access_token(refresh_token)


class TestRateLimiter:
    """Tests for rate limiter"""
    
    def test_allow_within_limit(self):
        """Test allowing requests within limit"""
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=100)
        
        for _ in range(5):
            assert limiter.is_allowed("client1") is True
    
    def test_block_over_minute_limit(self):
        """Test blocking when minute limit exceeded"""
        limiter = RateLimiter(requests_per_minute=3, requests_per_hour=100)
        
        # Use all allowed requests
        for _ in range(3):
            assert limiter.is_allowed("client2") is True
        
        # Next request should be blocked
        assert limiter.is_allowed("client2") is False
    
    def test_different_clients_separate_limits(self):
        """Test that different clients have separate limits"""
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)
        
        # Client A uses all requests
        assert limiter.is_allowed("clientA") is True
        assert limiter.is_allowed("clientA") is True
        assert limiter.is_allowed("clientA") is False
        
        # Client B should still be allowed
        assert limiter.is_allowed("clientB") is True
    
    def test_get_retry_after(self):
        """Test getting retry after time"""
        limiter = RateLimiter(requests_per_minute=1, requests_per_hour=100)
        
        limiter.is_allowed("client3")
        limiter.is_allowed("client3")  # This exceeds limit
        
        retry_after = limiter.get_retry_after("client3")
        assert retry_after >= 0
        assert retry_after <= 60


class TestAuthRouteSchemas:
    """Tests for auth route schemas"""
    
    def test_register_request_valid(self):
        """Test valid registration request"""
        from myome.api.routes.auth import RegisterRequest
        
        request = RegisterRequest(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )
        
        assert request.email == "test@example.com"
        assert request.password == "password123"
    
    def test_register_request_invalid_email(self):
        """Test registration with invalid email"""
        from myome.api.routes.auth import RegisterRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="password123",
            )
    
    def test_login_request(self):
        """Test login request schema"""
        from myome.api.routes.auth import LoginRequest
        
        request = LoginRequest(
            email="user@example.com",
            password="mypassword",
        )
        
        assert request.email == "user@example.com"


class TestUserRouteSchemas:
    """Tests for user route schemas"""
    
    def test_user_read_schema(self):
        """Test user read schema"""
        from myome.api.routes.users import UserRead
        
        user_data = {
            "id": "user-123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
        }
        
        user = UserRead(**user_data)
        assert user.id == "user-123"
        assert user.is_active is True
    
    def test_user_update_schema(self):
        """Test user update schema"""
        from myome.api.routes.users import UserUpdate
        
        update = UserUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None


class TestHealthRouteSchemas:
    """Tests for health route schemas"""
    
    def test_heart_rate_create(self):
        """Test heart rate creation schema"""
        from myome.api.routes.health import HeartRateCreate
        
        reading = HeartRateCreate(
            timestamp=datetime.now(timezone.utc),
            heart_rate_bpm=72,
            activity_type="resting",
        )
        
        assert reading.heart_rate_bpm == 72
        assert reading.activity_type == "resting"
    
    def test_glucose_create(self):
        """Test glucose creation schema"""
        from myome.api.routes.health import GlucoseCreate
        
        reading = GlucoseCreate(
            timestamp=datetime.now(timezone.utc),
            glucose_mg_dl=105.5,
            meal_context="fasting",
        )
        
        assert reading.glucose_mg_dl == 105.5
        assert reading.meal_context == "fasting"


class TestDeviceRouteSchemas:
    """Tests for device route schemas"""
    
    def test_device_create(self):
        """Test device creation schema"""
        from myome.api.routes.devices import DeviceCreate
        from myome.core.models import DeviceType, DeviceVendor
        
        device = DeviceCreate(
            name="My Oura Ring",
            device_type=DeviceType.SMART_RING,
            vendor=DeviceVendor.OURA,
            model="Gen 3",
        )
        
        assert device.name == "My Oura Ring"
        assert device.device_type == DeviceType.SMART_RING
    
    def test_device_sync_request(self):
        """Test device sync request schema"""
        from myome.api.routes.devices import DeviceSyncRequest
        
        request = DeviceSyncRequest(hours_back=48)
        assert request.hours_back == 48
        
        # Test default
        default_request = DeviceSyncRequest()
        assert default_request.hours_back == 24


class TestAlertRouteSchemas:
    """Tests for alert route schemas"""
    
    def test_alert_response(self):
        """Test alert response schema"""
        from myome.api.routes.alerts import AlertResponse
        
        alert = AlertResponse(
            id="alert-123",
            created_at="2026-01-15T10:00:00Z",
            status="active",
            priority="high",
            title="High glucose alert",
            message="Glucose reading above normal",
            recommendation="Check your diet",
            biomarker="glucose",
            value=185.0,
        )
        
        assert alert.id == "alert-123"
        assert alert.priority == "high"
        assert alert.value == 185.0
