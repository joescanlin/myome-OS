"""Tests for sensor abstraction layer"""

from datetime import UTC, datetime, timedelta

import pytest

from myome.sensors.adapters.generic import ManualEntrySensor
from myome.sensors.base import (
    CalibrationParams,
    DataQuality,
    Measurement,
    SensorType,
)
from myome.sensors.calibration.kalman import KalmanCalibrator, MultiPointCalibrator
from myome.sensors.normalizer import DataNormalizer
from myome.sensors.registry import SensorRegistry


class TestMeasurement:
    """Tests for Measurement dataclass"""

    def test_measurement_creation(self):
        """Test creating a measurement"""
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=72.0,
            unit="bpm",
            sensor_type=SensorType.HEART_RATE,
            confidence=0.95,
            quality=DataQuality.HIGH,
        )
        assert m.value == 72.0
        assert m.unit == "bpm"
        assert m.sensor_type == SensorType.HEART_RATE
        assert m.confidence == 0.95

    def test_measurement_to_dict(self):
        """Test measurement serialization"""
        now = datetime.now(UTC)
        m = Measurement(
            timestamp=now,
            value=100.0,
            unit="mg/dL",
            sensor_type=SensorType.GLUCOSE,
        )
        d = m.to_dict()
        assert d["value"] == 100.0
        assert d["unit"] == "mg/dL"
        assert d["sensor_type"] == "glucose"
        assert d["timestamp"] == now.isoformat()


class TestCalibrationParams:
    """Tests for CalibrationParams"""

    def test_default_calibration(self):
        """Test default calibration is identity"""
        params = CalibrationParams()
        assert params.apply(100.0) == 100.0
        assert params.apply(0.0) == 0.0

    def test_scaling_calibration(self):
        """Test calibration with scaling factor"""
        # Formula: alpha * (raw_value - beta) + gamma
        # With alpha=1.1, beta=0, gamma=0: 1.1 * (100 - 0) + 0 = 110
        params = CalibrationParams(alpha=1.1, beta=0.0, gamma=0.0)
        assert abs(params.apply(100.0) - 110.0) < 0.001

    def test_offset_calibration(self):
        """Test calibration with offset"""
        params = CalibrationParams(alpha=1.0, beta=5.0, gamma=10.0)
        # Result: 1.0 * (100 - 5) + 10 = 105
        assert params.apply(100.0) == 105.0


class TestDataNormalizer:
    """Tests for DataNormalizer"""

    def test_normalize_heart_rate_bpm(self):
        """Test normalizing heart rate in bpm (no change)"""
        normalizer = DataNormalizer()
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=72.0,
            unit="bpm",
            sensor_type=SensorType.HEART_RATE,
        )
        normalized = normalizer.normalize(m)
        assert normalized is not None
        assert normalized.value == 72.0
        assert normalized.unit == "bpm"

    def test_normalize_heart_rate_invalid(self):
        """Test normalizing invalid heart rate returns None"""
        normalizer = DataNormalizer()
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=500.0,  # Impossible HR
            unit="bpm",
            sensor_type=SensorType.HEART_RATE,
        )
        normalized = normalizer.normalize(m)
        assert normalized is None

    def test_normalize_glucose_mmol(self):
        """Test converting glucose from mmol/L to mg/dL"""
        normalizer = DataNormalizer()
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=5.5,  # 5.5 mmol/L
            unit="mmol/L",
            sensor_type=SensorType.GLUCOSE,
        )
        normalized = normalizer.normalize(m)
        assert normalized is not None
        assert normalized.unit == "mg/dL"
        assert abs(normalized.value - 99.1) < 1.0  # ~99 mg/dL

    def test_normalize_weight_lbs(self):
        """Test converting weight from lbs to kg"""
        normalizer = DataNormalizer()
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=165.0,  # 165 lbs
            unit="lbs",
            sensor_type=SensorType.BODY_COMPOSITION,
        )
        normalized = normalizer.normalize(m)
        assert normalized is not None
        assert normalized.unit == "kg"
        assert abs(normalized.value - 74.84) < 0.1  # ~75 kg

    def test_normalize_temperature_fahrenheit(self):
        """Test converting temperature from F to C"""
        normalizer = DataNormalizer()
        m = Measurement(
            timestamp=datetime.now(UTC),
            value=98.6,  # Normal body temp in F
            unit="fahrenheit",
            sensor_type=SensorType.TEMPERATURE,
        )
        normalized = normalizer.normalize(m)
        assert normalized is not None
        assert normalized.unit == "celsius"
        assert abs(normalized.value - 37.0) < 0.1

    def test_detect_outliers(self):
        """Test outlier detection"""
        import random

        random.seed(42)

        normalizer = DataNormalizer()

        # Create measurements with variance and one outlier
        base_time = datetime.now(UTC)
        measurements = []
        for i in range(20):
            if i == 15:
                value = 200.0  # Outlier
            else:
                value = 70.0 + random.uniform(-5, 5)  # Normal HR with variance
            measurements.append(
                Measurement(
                    timestamp=base_time + timedelta(minutes=i),
                    value=value,
                    unit="bpm",
                    sensor_type=SensorType.HEART_RATE,
                )
            )

        # Detect outliers
        outliers = normalizer.detect_outliers(
            measurements, window_size=5, threshold_std=3.0
        )
        assert len(outliers) >= 1
        # The outlier should be the value 200.0
        outlier_values = [o[0].value for o in outliers]
        assert 200.0 in outlier_values


class TestKalmanCalibrator:
    """Tests for Kalman filter calibration"""

    def test_initial_calibration(self):
        """Test initial calibration is identity"""
        cal = KalmanCalibrator()
        params = cal.get_params()
        assert abs(params.alpha - 1.0) < 0.01
        assert abs(params.beta - 0.0) < 0.01

    def test_calibration_update(self):
        """Test calibration updates with reference"""
        cal = KalmanCalibrator()

        # Provide some calibration references
        # Sensor reads 100, reference is 95 -> sensor reads high
        cal.update(100.0, 95.0)
        cal.update(110.0, 104.5)
        cal.update(90.0, 85.5)

        cal.get_params()

        # After updates, calibrated value should be closer to reference
        calibrated = cal.calibrate(100.0)
        assert abs(calibrated - 95.0) < 5.0  # Should be closer to 95

    def test_calibration_reset(self):
        """Test resetting calibration"""
        cal = KalmanCalibrator()
        cal.update(100.0, 90.0)
        cal.reset()

        params = cal.get_params()
        assert abs(params.alpha - 1.0) < 0.01
        assert abs(params.beta - 0.0) < 0.01


class TestMultiPointCalibrator:
    """Tests for multi-point calibration"""

    def test_insufficient_points(self):
        """Test calibration fails with insufficient points"""
        cal = MultiPointCalibrator(min_points=3)
        cal.add_reference(100.0, 95.0)
        cal.add_reference(110.0, 104.5)

        params = cal.calibrate()
        assert params is None  # Not enough points

    def test_linear_calibration(self):
        """Test linear calibration with multiple points"""
        cal = MultiPointCalibrator(min_points=3)

        # Add points on a line: reference = 0.95 * sensor + 0
        cal.add_reference(100.0, 95.0)
        cal.add_reference(110.0, 104.5)
        cal.add_reference(90.0, 85.5)
        cal.add_reference(120.0, 114.0)

        params = cal.calibrate()
        assert params is not None
        assert abs(params.alpha - 0.95) < 0.01
        assert abs(params.beta - 0.0) < 1.0


class TestManualEntrySensor:
    """Tests for manual entry sensor"""

    def test_manual_entry_creation(self):
        """Test creating a manual entry sensor"""
        sensor = ManualEntrySensor(
            sensor_type=SensorType.GLUCOSE,
            unit="mg/dL",
            user_id="test-user",
        )
        assert sensor.sensor_type == SensorType.GLUCOSE
        assert sensor.sensor_id == "manual:test-user:glucose"

    def test_add_measurement(self):
        """Test adding manual measurements"""
        sensor = ManualEntrySensor(
            sensor_type=SensorType.GLUCOSE,
            unit="mg/dL",
            user_id="test-user",
        )

        now = datetime.now(UTC)
        m = sensor.add_measurement(now, 105.0, notes="Before breakfast")

        assert m.value == 105.0
        assert m.metadata.get("notes") == "Before breakfast"

    @pytest.mark.asyncio
    async def test_get_historical(self):
        """Test retrieving historical measurements"""
        sensor = ManualEntrySensor(
            sensor_type=SensorType.GLUCOSE,
            unit="mg/dL",
            user_id="test-user",
        )

        base = datetime.now(UTC)
        sensor.add_measurement(base - timedelta(hours=2), 100.0)
        sensor.add_measurement(base - timedelta(hours=1), 110.0)
        sensor.add_measurement(base, 95.0)

        # Get last 90 minutes
        start = base - timedelta(minutes=90)
        end = base + timedelta(minutes=1)

        measurements = await sensor.get_historical(start, end)
        assert len(measurements) == 2  # Should exclude the 2-hour-old one


class TestSensorRegistry:
    """Tests for sensor registry"""

    def test_list_adapters(self):
        """Test listing registered adapters"""
        adapters = SensorRegistry.list_adapters()
        assert "dexcom:glucose" in adapters

    def test_list_device_adapters(self):
        """Test listing registered device adapters"""
        devices = SensorRegistry.list_device_adapters()
        assert "oura" in devices

    def test_get_adapter(self):
        """Test getting an adapter by vendor and type"""
        adapter = SensorRegistry.get_adapter("dexcom", SensorType.GLUCOSE)
        assert adapter is not None

    def test_get_device_adapter(self):
        """Test getting a device adapter by vendor"""
        adapter = SensorRegistry.get_device_adapter("oura")
        assert adapter is not None
