"""Withings data sync service"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from myome.core.logging import logger
from myome.integrations.oauth import OAuthTokens, WithingsOAuth
from myome.core.config import settings


class WithingsSyncService:
    """Service to sync data from Withings API"""
    
    BASE_URL = "https://wbsapi.withings.net"
    
    # Withings measurement types
    MEASURE_TYPES = {
        1: "weight",           # kg
        4: "height",           # meters
        5: "fat_free_mass",    # kg
        6: "fat_ratio",        # %
        8: "fat_mass_weight",  # kg
        9: "diastolic_bp",     # mmHg
        10: "systolic_bp",     # mmHg
        11: "heart_pulse",     # bpm
        76: "muscle_mass",     # kg
        77: "hydration",       # kg
        88: "bone_mass",       # kg
        91: "pulse_wave_velocity",
    }
    
    def __init__(self, tokens: OAuthTokens):
        self.tokens = tokens
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def ensure_valid_token(self) -> OAuthTokens:
        """Refresh token if expired"""
        if self.tokens.is_expired():
            oauth = WithingsOAuth(
                client_id=settings.withings_client_id,
                client_secret=settings.withings_client_secret,
                redirect_uri=settings.withings_redirect_uri,
            )
            try:
                self.tokens = await oauth.refresh_tokens(self.tokens.refresh_token)
            finally:
                await oauth.close()
        return self.tokens
    
    async def _api_call(self, endpoint: str, params: dict) -> dict:
        """Make authenticated API call"""
        await self.ensure_valid_token()
        
        params["access_token"] = self.tokens.access_token
        response = await self.client.post(endpoint, data=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") != 0:
            raise Exception(f"Withings API error: {data}")
        
        return data.get("body", {})
    
    async def get_measurements(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        measure_types: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Get measurements (weight, body composition, blood pressure).
        Returns raw measurement groups.
        """
        params = {
            "action": "getmeas",
        }
        
        if start:
            params["startdate"] = int(start.timestamp())
        if end:
            params["enddate"] = int(end.timestamp())
        if measure_types:
            params["meastypes"] = ",".join(str(t) for t in measure_types)
        
        body = await self._api_call("/measure", params)
        return body.get("measuregrps", [])
    
    async def get_activity(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Get activity data (steps, distance, calories)"""
        params = {
            "action": "getactivity",
            "data_fields": "steps,distance,elevation,soft,moderate,intense,active,calories,totalcalories,hr_average,hr_min,hr_max",
        }
        
        if start:
            params["startdateymd"] = start.strftime("%Y-%m-%d")
        if end:
            params["enddateymd"] = end.strftime("%Y-%m-%d")
        
        body = await self._api_call("/v2/measure", params)
        return body.get("activities", [])
    
    async def get_sleep(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Get sleep summary data"""
        params = {
            "action": "getsummary",
            "data_fields": "breathing_disturbances_intensity,deepsleepduration,durationtosleep,durationtowakeup,hr_average,hr_max,hr_min,lightsleepduration,remsleepduration,rr_average,rr_max,rr_min,sleep_score,snoring,snoringepisodecount,wakeupcount,wakeupduration",
        }
        
        if start:
            params["startdateymd"] = start.strftime("%Y-%m-%d")
        if end:
            params["enddateymd"] = end.strftime("%Y-%m-%d")
        
        body = await self._api_call("/v2/sleep", params)
        return body.get("series", [])
    
    def _parse_measurement_value(self, measure: dict) -> float:
        """Parse Withings measurement value (value * 10^unit)"""
        value = measure.get("value", 0)
        unit = measure.get("unit", 0)
        return value * (10 ** unit)
    
    async def sync_all_data(
        self,
        user_id: str,
        device_id: str,
        days_back: int = 30,
    ) -> dict:
        """
        Sync all Withings data to Myome database.
        Returns count of records synced per type.
        """
        from myome.core.database import async_session_factory
        from myome.core.models import (
            HeartRateReading, BodyComposition, SleepSession,
        )
        
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)
        
        counts = {
            "weight": 0,
            "blood_pressure": 0,
            "sleep": 0,
            "activity": 0,
        }
        
        async with async_session_factory() as session:
            # Sync measurements (weight, body comp, BP)
            try:
                measure_groups = await self.get_measurements(start, end)
                
                for group in measure_groups:
                    timestamp = datetime.fromtimestamp(
                        group["date"], tz=timezone.utc
                    )
                    
                    # Parse all measures in this group
                    measures = {}
                    for m in group.get("measures", []):
                        measure_type = m.get("type")
                        if measure_type in self.MEASURE_TYPES:
                            name = self.MEASURE_TYPES[measure_type]
                            measures[name] = self._parse_measurement_value(m)
                    
                    # Body composition (weight, fat, muscle, etc)
                    if "weight" in measures:
                        body_comp = BodyComposition(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            weight_kg=measures.get("weight"),
                            body_fat_pct=measures.get("fat_ratio"),
                            muscle_mass_kg=measures.get("muscle_mass"),
                            bone_mass_kg=measures.get("bone_mass"),
                            water_pct=measures.get("hydration") / measures.get("weight", 1) * 100 if measures.get("hydration") and measures.get("weight") else None,
                        )
                        session.add(body_comp)
                        counts["weight"] += 1
                    
                    # Blood pressure reading
                    if "systolic_bp" in measures and "diastolic_bp" in measures:
                        # Store as heart rate reading with BP in metadata
                        # TODO: Create proper BloodPressure model
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=int(measures.get("heart_pulse", 0)) if measures.get("heart_pulse") else 60,
                            activity_type="blood_pressure",
                        )
                        session.add(hr)
                        counts["blood_pressure"] += 1
                
                await session.commit()
                logger.info(f"Synced {counts['weight']} weight, {counts['blood_pressure']} BP records from Withings")
            except Exception as e:
                logger.error(f"Failed to sync Withings measurements: {e}")
                await session.rollback()
            
            # Sync sleep data
            try:
                sleep_records = await self.get_sleep(start, end)
                
                for record in sleep_records:
                    start_time = datetime.fromtimestamp(
                        record.get("startdate", 0), tz=timezone.utc
                    )
                    end_time = datetime.fromtimestamp(
                        record.get("enddate", 0), tz=timezone.utc
                    )
                    
                    total_sleep = (
                        record.get("lightsleepduration", 0) +
                        record.get("deepsleepduration", 0) +
                        record.get("remsleepduration", 0)
                    ) // 60  # Convert to minutes
                    
                    sleep = SleepSession(
                        user_id=user_id,
                        device_id=device_id,
                        start_time=start_time,
                        end_time=end_time,
                        total_sleep_minutes=total_sleep,
                        time_in_bed_minutes=int((end_time - start_time).total_seconds() / 60),
                        deep_sleep_minutes=record.get("deepsleepduration", 0) // 60,
                        rem_sleep_minutes=record.get("remsleepduration", 0) // 60,
                        light_sleep_minutes=record.get("lightsleepduration", 0) // 60,
                        awake_minutes=record.get("wakeupduration", 0) // 60,
                        sleep_score=record.get("sleep_score"),
                        avg_heart_rate_bpm=record.get("hr_average"),
                        avg_respiratory_rate=record.get("rr_average"),
                    )
                    session.add(sleep)
                    counts["sleep"] += 1
                
                await session.commit()
                logger.info(f"Synced {counts['sleep']} sleep records from Withings")
            except Exception as e:
                logger.error(f"Failed to sync Withings sleep: {e}")
                await session.rollback()
            
            # Sync activity data (HR from activity)
            try:
                activity_records = await self.get_activity(start, end)
                
                for record in activity_records:
                    date_str = record.get("date")
                    if not date_str:
                        continue
                    
                    timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(
                        hour=12, tzinfo=timezone.utc
                    )
                    
                    # Store average HR if available
                    if record.get("hr_average"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=record["hr_average"],
                            activity_type="daily_average",
                        )
                        session.add(hr)
                        counts["activity"] += 1
                
                await session.commit()
                logger.info(f"Synced {counts['activity']} activity records from Withings")
            except Exception as e:
                logger.error(f"Failed to sync Withings activity: {e}")
                await session.rollback()
        
        return counts
