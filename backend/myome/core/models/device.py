"""Device and sensor models"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myome.core.database import Base
from myome.core.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from myome.core.models.user import User


class DeviceType(str, PyEnum):
    """Supported device types"""

    SMARTWATCH = "smartwatch"
    FITNESS_TRACKER = "fitness_tracker"
    CGM = "cgm"  # Continuous glucose monitor
    SMART_RING = "smart_ring"
    SMART_SCALE = "smart_scale"
    BLOOD_PRESSURE = "blood_pressure"
    PULSE_OXIMETER = "pulse_oximeter"
    THERMOMETER = "thermometer"
    SLEEP_TRACKER = "sleep_tracker"
    AIR_QUALITY = "air_quality"
    OTHER = "other"


class DeviceVendor(str, PyEnum):
    """Supported device vendors"""

    APPLE = "apple"
    GARMIN = "garmin"
    FITBIT = "fitbit"
    OURA = "oura"
    WHOOP = "whoop"
    WITHINGS = "withings"
    DEXCOM = "dexcom"
    ABBOTT = "abbott"  # Libre CGM
    LEVELS = "levels"
    POLAR = "polar"
    AWAIR = "awair"
    EVE = "eve"
    GENERIC = "generic"


class Device(Base, UUIDMixin, TimestampMixin):
    """Connected health device"""

    __tablename__ = "devices"

    # Foreign key
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Device identification
    device_type: Mapped[str] = mapped_column(
        ENUM(
            "smartwatch",
            "fitness_tracker",
            "cgm",
            "smart_ring",
            "smart_scale",
            "blood_pressure",
            "pulse_oximeter",
            "thermometer",
            "sleep_tracker",
            "air_quality",
            "other",
            name="devicetype",
            create_type=False,
        ),
        nullable=False,
    )
    vendor: Mapped[str] = mapped_column(
        ENUM(
            "apple",
            "garmin",
            "fitbit",
            "oura",
            "whoop",
            "withings",
            "dexcom",
            "abbott",
            "levels",
            "polar",
            "awair",
            "eve",
            "generic",
            name="devicevendor",
            create_type=False,
        ),
        nullable=False,
    )
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Display name
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Connection status
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # API credentials (encrypted in production)
    api_credentials: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Calibration parameters
    calibration_params: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Device-specific metadata
    device_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return f"<Device {self.name} ({self.vendor}/{self.device_type})>"


class DeviceReading(Base, UUIDMixin):
    """Generic device reading for non-specialized data"""

    __tablename__ = "device_readings"

    # Foreign keys
    device_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("devices.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Timestamp (for time-series indexing)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Reading type and value
    reading_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    # Quality/confidence
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Raw data
    raw_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
