"""Tests for Pydantic schemas"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from myome.api.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
    HeartRateCreate,
    HeartRateRead,
    GlucoseCreate,
    GlucoseRead,
)
from myome.api.schemas.health import (
    HRVCreate,
    SleepSessionCreate,
    ActivityCreate,
    BodyCompositionCreate,
)


class TestUserSchemas:
    """Tests for user schemas"""
    
    def test_user_create_valid(self):
        """Test valid user creation schema"""
        user = UserCreate(
            email="test@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@example.com"
        assert user.password == "securepassword123"
    
    def test_user_create_invalid_email(self):
        """Test invalid email is rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="securepassword123",
            )
    
    def test_user_create_short_password(self):
        """Test short password is rejected"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short",  # Less than 8 characters
            )
    
    def test_user_update_partial(self):
        """Test partial user update"""
        update = UserUpdate(first_name="Jane")
        assert update.first_name == "Jane"
        assert update.last_name is None


class TestHealthSchemas:
    """Tests for health data schemas"""
    
    def test_heart_rate_create_valid(self):
        """Test valid heart rate creation"""
        hr = HeartRateCreate(
            timestamp=datetime.now(timezone.utc),
            heart_rate_bpm=72,
            activity_type="resting",
        )
        assert hr.heart_rate_bpm == 72
    
    def test_heart_rate_invalid_bpm_low(self):
        """Test heart rate below minimum is rejected"""
        with pytest.raises(ValidationError):
            HeartRateCreate(
                timestamp=datetime.now(timezone.utc),
                heart_rate_bpm=15,  # Below 20
            )
    
    def test_heart_rate_invalid_bpm_high(self):
        """Test heart rate above maximum is rejected"""
        with pytest.raises(ValidationError):
            HeartRateCreate(
                timestamp=datetime.now(timezone.utc),
                heart_rate_bpm=350,  # Above 300
            )
    
    def test_glucose_create_valid(self):
        """Test valid glucose creation"""
        glucose = GlucoseCreate(
            timestamp=datetime.now(timezone.utc),
            glucose_mg_dl=105.0,
            trend="rising",
            meal_context="post_meal",
        )
        assert glucose.glucose_mg_dl == 105.0
    
    def test_glucose_invalid_value_low(self):
        """Test glucose below minimum is rejected"""
        with pytest.raises(ValidationError):
            GlucoseCreate(
                timestamp=datetime.now(timezone.utc),
                glucose_mg_dl=10.0,  # Below 20
            )
    
    def test_hrv_create_valid(self):
        """Test valid HRV creation"""
        hrv = HRVCreate(
            timestamp=datetime.now(timezone.utc),
            sdnn_ms=45.5,
            rmssd_ms=38.2,
            pnn50_pct=22.0,
        )
        assert hrv.sdnn_ms == 45.5
        assert hrv.rmssd_ms == 38.2
    
    def test_sleep_session_create_valid(self):
        """Test valid sleep session creation"""
        now = datetime.now(timezone.utc)
        sleep = SleepSessionCreate(
            start_time=now,
            end_time=now,
            total_sleep_minutes=420,
            time_in_bed_minutes=480,
            deep_sleep_minutes=90,
            rem_sleep_minutes=100,
            sleep_efficiency_pct=87.5,
            sleep_score=85,
        )
        assert sleep.total_sleep_minutes == 420
        assert sleep.sleep_score == 85
    
    def test_activity_create_valid(self):
        """Test valid activity creation"""
        activity = ActivityCreate(
            timestamp=datetime.now(timezone.utc),
            steps=10000,
            distance_meters=8000.0,
            calories_burned=400.0,
            active_minutes=60,
        )
        assert activity.steps == 10000
    
    def test_body_composition_valid(self):
        """Test valid body composition creation"""
        body = BodyCompositionCreate(
            timestamp=datetime.now(timezone.utc),
            weight_kg=75.5,
            body_fat_pct=18.5,
            muscle_mass_kg=35.0,
        )
        assert body.weight_kg == 75.5
    
    def test_body_composition_invalid_weight(self):
        """Test body weight below minimum is rejected"""
        with pytest.raises(ValidationError):
            BodyCompositionCreate(
                timestamp=datetime.now(timezone.utc),
                weight_kg=10.0,  # Below 20
            )
