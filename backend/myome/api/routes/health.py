"""Health data routes"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from myome.analytics.service import AnalyticsService
from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.core.models import HeartRateReading, GlucoseReading, SleepSession

router = APIRouter(prefix="/health", tags=["Health Data"])


class HeartRateCreate(BaseModel):
    """Heart rate creation request"""
    timestamp: datetime
    heart_rate_bpm: int
    activity_type: Optional[str] = None
    confidence: Optional[float] = None
    device_id: Optional[str] = None


class HeartRateRead(BaseModel):
    """Heart rate response"""
    timestamp: datetime
    heart_rate_bpm: int
    activity_type: Optional[str] = None
    confidence: Optional[float] = None
    device_id: Optional[str] = None
    
    model_config = {"from_attributes": True}


class GlucoseCreate(BaseModel):
    """Glucose creation request"""
    timestamp: datetime
    glucose_mg_dl: float
    trend: Optional[str] = None
    meal_context: Optional[str] = None
    device_id: Optional[str] = None


class GlucoseRead(BaseModel):
    """Glucose response"""
    timestamp: datetime
    glucose_mg_dl: float
    trend: Optional[str] = None
    meal_context: Optional[str] = None
    device_id: Optional[str] = None
    
    model_config = {"from_attributes": True}


# ============== Heart Rate ==============

@router.get("/heart-rate")
async def get_heart_rate(
    user: CurrentUser,
    session: DbSession,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, le=10000),
) -> list[HeartRateRead]:
    """Get heart rate readings"""
    query = select(HeartRateReading).where(
        HeartRateReading.user_id == user.id
    )
    
    if start:
        query = query.where(HeartRateReading.timestamp >= start)
    if end:
        query = query.where(HeartRateReading.timestamp <= end)
    
    query = query.order_by(HeartRateReading.timestamp.desc()).limit(limit)
    
    result = await session.execute(query)
    readings = result.scalars().all()
    
    return [HeartRateRead.model_validate(r) for r in readings]


@router.post("/heart-rate", status_code=status.HTTP_201_CREATED)
async def add_heart_rate(
    reading: HeartRateCreate,
    user: CurrentUser,
    session: DbSession,
) -> HeartRateRead:
    """Add manual heart rate reading"""
    hr = HeartRateReading(
        timestamp=reading.timestamp,
        user_id=user.id,
        heart_rate_bpm=reading.heart_rate_bpm,
        activity_type=reading.activity_type,
        confidence=reading.confidence,
        device_id=reading.device_id,
    )
    session.add(hr)
    await session.commit()
    await session.refresh(hr)
    
    return HeartRateRead.model_validate(hr)


# ============== Glucose ==============

@router.get("/glucose")
async def get_glucose(
    user: CurrentUser,
    session: DbSession,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, le=10000),
) -> list[GlucoseRead]:
    """Get glucose readings"""
    query = select(GlucoseReading).where(
        GlucoseReading.user_id == user.id
    )
    
    if start:
        query = query.where(GlucoseReading.timestamp >= start)
    if end:
        query = query.where(GlucoseReading.timestamp <= end)
    
    query = query.order_by(GlucoseReading.timestamp.desc()).limit(limit)
    
    result = await session.execute(query)
    readings = result.scalars().all()
    
    return [GlucoseRead.model_validate(r) for r in readings]


@router.post("/glucose", status_code=status.HTTP_201_CREATED)
async def add_glucose(
    reading: GlucoseCreate,
    user: CurrentUser,
    session: DbSession,
) -> GlucoseRead:
    """Add manual glucose reading"""
    glucose = GlucoseReading(
        timestamp=reading.timestamp,
        user_id=user.id,
        glucose_mg_dl=reading.glucose_mg_dl,
        trend=reading.trend,
        meal_context=reading.meal_context,
        device_id=reading.device_id,
    )
    session.add(glucose)
    await session.commit()
    await session.refresh(glucose)
    
    return GlucoseRead.model_validate(glucose)


# ============== Sleep ==============

@router.get("/sleep")
async def get_sleep_sessions(
    user: CurrentUser,
    session: DbSession,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=30, le=365),
) -> list[dict]:
    """Get sleep sessions"""
    query = select(SleepSession).where(
        SleepSession.user_id == user.id
    )
    
    if start:
        query = query.where(SleepSession.start_time >= start)
    if end:
        query = query.where(SleepSession.start_time <= end)
    
    query = query.order_by(SleepSession.start_time.desc()).limit(limit)
    
    result = await session.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "total_sleep_minutes": s.total_sleep_minutes,
            "deep_sleep_minutes": s.deep_sleep_minutes,
            "rem_sleep_minutes": s.rem_sleep_minutes,
            "light_sleep_minutes": s.light_sleep_minutes,
            "sleep_efficiency_pct": s.sleep_efficiency_pct,
            "sleep_score": s.sleep_score,
            "avg_heart_rate_bpm": s.avg_heart_rate_bpm,
            "avg_hrv_ms": s.avg_hrv_ms,
        }
        for s in sessions
    ]


# ============== Analytics ==============

@router.get("/analytics/daily")
async def get_daily_analysis(
    user: CurrentUser,
    date: Optional[datetime] = Query(default=None),
) -> dict:
    """Get daily health analysis"""
    service = AnalyticsService(user.id)
    return await service.run_daily_analysis(date)


@router.get("/analytics/score")
async def get_health_score(
    user: CurrentUser,
    date: Optional[datetime] = Query(default=None),
) -> dict:
    """Get overall health score"""
    service = AnalyticsService(user.id)
    return await service.get_health_score(date)


@router.get("/analytics/correlations")
async def get_correlations(
    user: CurrentUser,
    days: int = Query(default=30, le=365),
) -> list[dict]:
    """Discover biomarker correlations"""
    from myome.analytics.correlation.engine import CorrelationEngine
    
    engine = CorrelationEngine(user.id)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    
    correlations = await engine.discover_all_correlations(
        biomarkers=['heart_rate', 'hrv_sdnn', 'glucose'],
        start=start,
        end=end,
    )
    
    return [c.to_dict() for c in correlations[:20]]


@router.get("/analytics/trends")
async def get_trends(
    user: CurrentUser,
    days: int = Query(default=30, le=365),
) -> list[dict]:
    """Get biomarker trends"""
    from myome.analytics.correlation.trends import TrendAnalyzer
    from myome.analytics.data_loader import TimeSeriesLoader
    
    loader = TimeSeriesLoader(user.id)
    analyzer = TrendAnalyzer()
    
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    
    df = await loader.load_multi_biomarker(
        start, end,
        biomarkers=['heart_rate', 'hrv_sdnn', 'glucose'],
        resample='1D',
    )
    
    trends = []
    for column in df.columns:
        trend = analyzer.compute_trend(df[column], column)
        if trend and trend.is_significant:
            trends.append(trend.to_dict())
    
    return trends
