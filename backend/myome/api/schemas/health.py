"""Health data schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HeartRateBase(BaseModel):
    """Base heart rate schema"""

    heart_rate_bpm: int = Field(..., ge=20, le=300)
    activity_type: str | None = None
    confidence: float | None = Field(None, ge=0, le=1)


class HeartRateCreate(HeartRateBase):
    """Schema for creating heart rate reading"""

    timestamp: datetime
    device_id: str | None = None


class HeartRateRead(HeartRateBase):
    """Schema for reading heart rate"""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    user_id: str
    device_id: str | None = None


class GlucoseBase(BaseModel):
    """Base glucose schema"""

    glucose_mg_dl: float = Field(..., ge=20, le=600)
    trend: str | None = None
    meal_context: str | None = None


class GlucoseCreate(GlucoseBase):
    """Schema for creating glucose reading"""

    timestamp: datetime
    device_id: str | None = None


class GlucoseRead(GlucoseBase):
    """Schema for reading glucose"""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    user_id: str
    is_calibrated: bool


class HRVBase(BaseModel):
    """Base HRV schema"""

    sdnn_ms: float | None = Field(None, ge=0)
    rmssd_ms: float | None = Field(None, ge=0)
    pnn50_pct: float | None = Field(None, ge=0, le=100)
    lf_power: float | None = None
    hf_power: float | None = None
    lf_hf_ratio: float | None = None


class HRVCreate(HRVBase):
    """Schema for creating HRV reading"""

    timestamp: datetime
    device_id: str | None = None
    measurement_duration_sec: int | None = None


class HRVRead(HRVBase):
    """Schema for reading HRV"""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    user_id: str


class SleepSessionBase(BaseModel):
    """Base sleep session schema"""

    start_time: datetime
    end_time: datetime
    total_sleep_minutes: int = Field(..., ge=0)
    time_in_bed_minutes: int = Field(..., ge=0)

    # Stage durations
    light_sleep_minutes: int | None = Field(None, ge=0)
    deep_sleep_minutes: int | None = Field(None, ge=0)
    rem_sleep_minutes: int | None = Field(None, ge=0)
    awake_minutes: int | None = Field(None, ge=0)

    # Quality
    sleep_efficiency_pct: float | None = Field(None, ge=0, le=100)
    sleep_score: int | None = Field(None, ge=0, le=100)

    # Physiological
    avg_heart_rate_bpm: int | None = None
    min_heart_rate_bpm: int | None = None
    avg_hrv_ms: float | None = None


class SleepSessionCreate(SleepSessionBase):
    """Schema for creating sleep session"""

    device_id: str | None = None


class SleepSessionRead(SleepSessionBase):
    """Schema for reading sleep session"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    device_id: str | None = None


class ActivityBase(BaseModel):
    """Base activity schema"""

    steps: int | None = Field(None, ge=0)
    distance_meters: float | None = Field(None, ge=0)
    calories_burned: float | None = Field(None, ge=0)
    active_minutes: int | None = Field(None, ge=0)
    activity_type: str | None = None
    intensity_level: str | None = None


class ActivityCreate(ActivityBase):
    """Schema for creating activity reading"""

    timestamp: datetime
    device_id: str | None = None


class ActivityRead(ActivityBase):
    """Schema for reading activity"""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    user_id: str


class BodyCompositionBase(BaseModel):
    """Base body composition schema"""

    weight_kg: float = Field(..., ge=20, le=500)
    body_fat_pct: float | None = Field(None, ge=0, le=100)
    lean_mass_kg: float | None = Field(None, ge=0)
    muscle_mass_kg: float | None = Field(None, ge=0)
    bone_mass_kg: float | None = Field(None, ge=0)
    water_pct: float | None = Field(None, ge=0, le=100)
    visceral_fat_level: int | None = Field(None, ge=0)
    bmr_kcal: int | None = Field(None, ge=0)
    metabolic_age: int | None = Field(None, ge=0)


class BodyCompositionCreate(BodyCompositionBase):
    """Schema for creating body composition"""

    timestamp: datetime
    device_id: str | None = None
    measurement_method: str | None = None


class BodyCompositionRead(BodyCompositionBase):
    """Schema for reading body composition"""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    user_id: str
