"""Tests for database models"""

import pytest
from datetime import date, datetime, timezone
from uuid import uuid4

from myome.core.models import (
    User,
    HealthProfile,
    Device,
    HeartRateReading,
    HRVReading,
    GlucoseReading,
    SleepSession,
    ActivityReading,
    BodyComposition,
)
from myome.core.models.device import DeviceType, DeviceVendor


class TestUserModel:
    """Tests for User model"""
    
    def test_user_creation(self):
        """Test creating a user instance"""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hashed_password_here",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_verified=False,
        )
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.is_active == True
        assert user.is_verified == False
    
    def test_user_full_name(self):
        """Test full_name property"""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hash",
            first_name="Jane",
            last_name="Smith",
        )
        assert user.full_name == "Jane Smith"
    
    def test_user_full_name_no_name(self):
        """Test full_name falls back to email prefix"""
        user = User(
            id=str(uuid4()),
            email="johndoe@example.com",
            hashed_password="hash",
        )
        assert user.full_name == "johndoe"
    
    def test_user_age_calculation(self):
        """Test age property calculation"""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hash",
            date_of_birth=date(1990, 1, 1),
        )
        # Age should be calculated correctly
        assert user.age is not None
        assert user.age >= 35  # As of 2026
    
    def test_user_age_none_when_no_dob(self):
        """Test age is None when no date of birth"""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hash",
        )
        assert user.age is None
    
    def test_user_repr(self):
        """Test user string representation"""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            hashed_password="hash",
        )
        assert repr(user) == "<User test@example.com>"


class TestDeviceModel:
    """Tests for Device model"""
    
    def test_device_creation(self):
        """Test creating a device instance"""
        device = Device(
            id=str(uuid4()),
            user_id=str(uuid4()),
            device_type=DeviceType.SMART_RING,
            vendor=DeviceVendor.OURA,
            name="My Oura Ring",
            is_connected=False,
        )
        assert device.device_type == DeviceType.SMART_RING
        assert device.vendor == DeviceVendor.OURA
        assert device.name == "My Oura Ring"
        assert device.is_connected == False
    
    def test_device_types_enum(self):
        """Test device type enum values"""
        assert DeviceType.CGM == "cgm"
        assert DeviceType.SMARTWATCH == "smartwatch"
        assert DeviceType.SMART_SCALE == "smart_scale"
    
    def test_device_vendors_enum(self):
        """Test device vendor enum values"""
        assert DeviceVendor.DEXCOM == "dexcom"
        assert DeviceVendor.APPLE == "apple"
        assert DeviceVendor.OURA == "oura"


class TestTimeSeriesModels:
    """Tests for time-series models"""
    
    def test_heart_rate_reading(self):
        """Test heart rate reading creation"""
        reading = HeartRateReading(
            timestamp=datetime.now(timezone.utc),
            user_id=str(uuid4()),
            heart_rate_bpm=72,
            activity_type="resting",
            confidence=0.95,
        )
        assert reading.heart_rate_bpm == 72
        assert reading.activity_type == "resting"
        assert reading.confidence == 0.95
    
    def test_hrv_reading(self):
        """Test HRV reading creation"""
        reading = HRVReading(
            timestamp=datetime.now(timezone.utc),
            user_id=str(uuid4()),
            sdnn_ms=45.5,
            rmssd_ms=38.2,
            pnn50_pct=22.1,
            lf_hf_ratio=1.8,
        )
        assert reading.sdnn_ms == 45.5
        assert reading.rmssd_ms == 38.2
    
    def test_glucose_reading(self):
        """Test glucose reading creation"""
        reading = GlucoseReading(
            timestamp=datetime.now(timezone.utc),
            user_id=str(uuid4()),
            glucose_mg_dl=105.0,
            trend="stable",
            is_calibrated=True,
        )
        assert reading.glucose_mg_dl == 105.0
        assert reading.trend == "stable"
        assert reading.is_calibrated == True
    
    def test_sleep_session(self):
        """Test sleep session creation"""
        now = datetime.now(timezone.utc)
        session = SleepSession(
            id=str(uuid4()),
            user_id=str(uuid4()),
            start_time=now,
            end_time=now,
            total_sleep_minutes=420,
            time_in_bed_minutes=480,
            deep_sleep_minutes=90,
            rem_sleep_minutes=100,
            light_sleep_minutes=230,
            sleep_efficiency_pct=87.5,
            sleep_score=85,
        )
        assert session.total_sleep_minutes == 420
        assert session.sleep_score == 85
    
    def test_activity_reading(self):
        """Test activity reading creation"""
        reading = ActivityReading(
            timestamp=datetime.now(timezone.utc),
            user_id=str(uuid4()),
            steps=8500,
            distance_meters=6800.0,
            calories_burned=350.5,
            active_minutes=45,
        )
        assert reading.steps == 8500
        assert reading.distance_meters == 6800.0
    
    def test_body_composition(self):
        """Test body composition creation"""
        reading = BodyComposition(
            timestamp=datetime.now(timezone.utc),
            user_id=str(uuid4()),
            weight_kg=75.5,
            body_fat_pct=18.5,
            muscle_mass_kg=35.2,
            bmr_kcal=1750,
        )
        assert reading.weight_kg == 75.5
        assert reading.body_fat_pct == 18.5
