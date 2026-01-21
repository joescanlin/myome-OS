"""Base sensor interface and types"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SensorType(str, Enum):
    """Types of health sensors"""

    HEART_RATE = "heart_rate"
    HRV = "hrv"
    GLUCOSE = "glucose"
    SLEEP = "sleep"
    ACTIVITY = "activity"
    BODY_COMPOSITION = "body_composition"
    BLOOD_PRESSURE = "blood_pressure"
    TEMPERATURE = "temperature"
    SPO2 = "spo2"
    RESPIRATORY_RATE = "respiratory_rate"
    STRESS = "stress"
    AIR_QUALITY = "air_quality"


class DataQuality(str, Enum):
    """Data quality levels"""

    HIGH = "high"  # Medical-grade or validated
    MEDIUM = "medium"  # Consumer device, generally reliable
    LOW = "low"  # Estimated or interpolated
    UNKNOWN = "unknown"


@dataclass
class Measurement:
    """A single measurement from a sensor"""

    timestamp: datetime
    value: float
    unit: str
    sensor_type: SensorType
    confidence: float = 1.0  # 0-1 confidence score
    quality: DataQuality = DataQuality.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "sensor_type": self.sensor_type.value,
            "confidence": self.confidence,
            "quality": self.quality.value,
            "metadata": self.metadata,
        }


@dataclass
class SensorMetadata:
    """Metadata about a sensor/device"""

    vendor: str
    model: str
    firmware_version: str | None = None
    serial_number: str | None = None
    battery_level: float | None = None
    last_calibration: datetime | None = None


@dataclass
class CalibrationParams:
    """Calibration parameters for a sensor"""

    alpha: float = 1.0  # Scaling factor
    beta: float = 0.0  # Offset
    gamma: float = 0.0  # Baseline adjustment
    lag_seconds: float = 0  # Temporal lag compensation
    updated_at: datetime | None = None

    def apply(self, raw_value: float) -> float:
        """Apply calibration to raw value"""
        return self.alpha * (raw_value - self.beta) + self.gamma


class HealthSensor(ABC):
    """Abstract base class for all health sensors"""

    @property
    @abstractmethod
    def sensor_id(self) -> str:
        """Unique identifier for this sensor instance"""
        pass

    @property
    @abstractmethod
    def sensor_type(self) -> SensorType:
        """Type of sensor"""
        pass

    @property
    @abstractmethod
    def metadata(self) -> SensorMetadata:
        """Sensor metadata"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to device/API"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and cleanup resources"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if sensor is connected"""
        pass

    @abstractmethod
    def stream_data(self) -> AsyncIterator[Measurement]:
        """Stream real-time measurements"""
        raise NotImplementedError

    @abstractmethod
    async def get_historical(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]:
        """Retrieve historical data for date range"""
        pass

    def get_calibration(self) -> CalibrationParams:
        """Get current calibration parameters"""
        return CalibrationParams()

    def set_calibration(self, params: CalibrationParams) -> None:
        """Update calibration parameters"""
        pass


class MultiSensorDevice(ABC):
    """Base class for devices that provide multiple sensor types (e.g., smartwatch)"""

    @property
    @abstractmethod
    def device_id(self) -> str:
        """Unique device identifier"""
        pass

    @property
    @abstractmethod
    def supported_sensors(self) -> list[SensorType]:
        """List of sensor types this device supports"""
        pass

    @abstractmethod
    def get_sensor(self, sensor_type: SensorType) -> HealthSensor | None:
        """Get a specific sensor from this device"""
        pass

    @abstractmethod
    async def sync_all(
        self, start: datetime, end: datetime
    ) -> dict[SensorType, list[Measurement]]:
        """Sync all sensors for a time range"""
        pass
