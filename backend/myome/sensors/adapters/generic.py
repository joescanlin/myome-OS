"""Generic adapter for manual data entry and CSV imports"""

from collections.abc import AsyncIterator
from datetime import datetime

from myome.sensors.base import (
    DataQuality,
    HealthSensor,
    Measurement,
    SensorMetadata,
    SensorType,
)


class ManualEntrySensor(HealthSensor):
    """Adapter for manually entered health data"""

    def __init__(
        self,
        sensor_type: SensorType,
        unit: str,
        user_id: str,
    ):
        self._sensor_type = sensor_type
        self._unit = unit
        self._user_id = user_id
        self._measurements: list[Measurement] = []
        self._metadata = SensorMetadata(
            vendor="manual",
            model="User Entry",
        )

    @property
    def sensor_id(self) -> str:
        return f"manual:{self._user_id}:{self._sensor_type.value}"

    @property
    def sensor_type(self) -> SensorType:
        return self._sensor_type

    @property
    def metadata(self) -> SensorMetadata:
        return self._metadata

    async def connect(self) -> None:
        pass  # No connection needed

    async def disconnect(self) -> None:
        pass

    async def is_connected(self) -> bool:
        return True

    def stream_data(self) -> AsyncIterator[Measurement]:
        """Manual entry doesn't support streaming"""
        raise NotImplementedError("Manual entry doesn't support streaming")

    async def get_historical(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]:
        """Return stored measurements within date range"""
        return [m for m in self._measurements if start <= m.timestamp <= end]

    def add_measurement(
        self,
        timestamp: datetime,
        value: float,
        notes: str | None = None,
    ) -> Measurement:
        """Add a manual measurement"""
        measurement = Measurement(
            timestamp=timestamp,
            value=value,
            unit=self._unit,
            sensor_type=self._sensor_type,
            confidence=1.0,  # User-reported
            quality=DataQuality.MEDIUM,
            metadata={"notes": notes} if notes else {},
        )
        self._measurements.append(measurement)
        return measurement
