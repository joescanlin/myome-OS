"""Time-series models for high-frequency health data (TimescaleDB hypertables)"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from myome.core.database import Base


class HeartRateReading(Base):
    """Heart rate measurements (hypertable)"""

    __tablename__ = "heart_rate_readings"

    # Composite primary key for TimescaleDB
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Measurements
    heart_rate_bpm: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional context
    device_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_hr_user_time", "user_id", "timestamp"),)


class HRVReading(Base):
    """Heart rate variability measurements (hypertable)"""

    __tablename__ = "hrv_readings"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Time-domain metrics
    sdnn_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmssd_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnn50_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Frequency-domain metrics
    lf_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    hf_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    lf_hf_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Context
    device_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    measurement_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_hrv_user_time", "user_id", "timestamp"),)


class GlucoseReading(Base):
    """Continuous glucose monitoring readings (hypertable)"""

    __tablename__ = "glucose_readings"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Glucose value
    glucose_mg_dl: Mapped[float] = mapped_column(Float, nullable=False)

    # Trend arrow (CGM specific)
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trend_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Calibration status
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=True)
    calibration_factor: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Context
    device_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    meal_context: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (Index("ix_glucose_user_time", "user_id", "timestamp"),)


class SleepSession(Base):
    """Sleep session summary"""

    __tablename__ = "sleep_sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Session timing
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Duration metrics (minutes)
    total_sleep_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    time_in_bed_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_onset_latency_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    wake_after_sleep_onset_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Stage durations (minutes)
    light_sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deep_sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rem_sleep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    awake_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality metrics
    sleep_efficiency_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Physiological metrics during sleep
    avg_heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_hrv_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_respiratory_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_spo2_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Device
    device_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    __table_args__ = (Index("ix_sleep_user_start", "user_id", "start_time"),)


class SleepEpoch(Base):
    """30-second sleep stage epochs (hypertable)"""

    __tablename__ = "sleep_epochs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sleep_sessions.id", ondelete="CASCADE"),
        index=True,
    )

    # Sleep stage: wake, light, deep, rem
    stage: Mapped[str] = mapped_column(String(20), nullable=False)

    # Optional metrics for this epoch
    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    movement_intensity: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_epoch_session", "session_id", "timestamp"),)


class ActivityReading(Base):
    """Activity and step count readings (hypertable)"""

    __tablename__ = "activity_readings"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Activity metrics
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Activity intensity
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    intensity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Heart rate zones (minutes)
    hr_zone_1_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_zone_2_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_zone_3_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_zone_4_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hr_zone_5_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    device_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    __table_args__ = (Index("ix_activity_user_time", "user_id", "timestamp"),)


class BodyComposition(Base):
    """Body composition measurements"""

    __tablename__ = "body_composition"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Weight
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Body composition (from smart scale or DEXA)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    lean_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    visceral_fat_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metabolic
    bmr_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metabolic_age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Source
    measurement_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    __table_args__ = (Index("ix_body_comp_user_time", "user_id", "timestamp"),)
