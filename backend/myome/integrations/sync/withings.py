"""Withings data sync service"""

from datetime import UTC, datetime, timedelta

import httpx

from myome.core.config import settings
from myome.core.logging import logger
from myome.integrations.oauth import OAuthTokens, WithingsOAuth


class WithingsSyncService:
    """Service to sync data from Withings API"""

    BASE_URL = "https://wbsapi.withings.net"

    # Withings measurement types
    MEASURE_TYPES = {
        1: "weight",  # kg
        4: "height",  # meters
        5: "fat_free_mass",  # kg
        6: "fat_ratio",  # %
        8: "fat_mass_weight",  # kg
        9: "diastolic_bp",  # mmHg
        10: "systolic_bp",  # mmHg
        11: "heart_pulse",  # bpm
        76: "muscle_mass",  # kg
        77: "hydration",  # kg
        88: "bone_mass",  # kg
        91: "pulse_wave_velocity",
    }

    def __init__(self, tokens: OAuthTokens):
        self.tokens = tokens
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def ensure_valid_token(self) -> OAuthTokens:
        """Refresh token if expired"""
        if self.tokens.is_expired():
            if self.tokens.refresh_token is None:
                raise ValueError("Withings refresh token missing")
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

    async def _api_call(self, endpoint: str, params: dict) -> dict[str, object]:
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
        start: datetime | None = None,
        end: datetime | None = None,
        measure_types: list[int] | None = None,
    ) -> list[dict[str, object]]:
        """
        Get measurements (weight, body composition, blood pressure).
        Returns raw measurement groups.
        """
        params: dict[str, str | int] = {
            "action": "getmeas",
        }

        if start:
            params["startdate"] = int(start.timestamp())
        if end:
            params["enddate"] = int(end.timestamp())
        if measure_types:
            params["meastypes"] = ",".join(str(t) for t in measure_types)

        body = await self._api_call("/measure", params)
        measure_groups = body.get("measuregrps")
        return list(measure_groups) if isinstance(measure_groups, list) else []

    async def get_activity(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Get activity data (steps, distance, calories)"""
        params: dict[str, str] = {
            "action": "getactivity",
            "data_fields": "steps,distance,elevation,soft,moderate,intense,active,calories,totalcalories,hr_average,hr_min,hr_max",
        }

        if start:
            params["startdateymd"] = start.strftime("%Y-%m-%d")
        if end:
            params["enddateymd"] = end.strftime("%Y-%m-%d")

        body = await self._api_call("/v2/measure", params)
        activities = body.get("activities")
        return list(activities) if isinstance(activities, list) else []

    async def get_sleep(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Get sleep summary data"""
        params: dict[str, str] = {
            "action": "getsummary",
            "data_fields": "breathing_disturbances_intensity,deepsleepduration,durationtosleep,durationtowakeup,hr_average,hr_max,hr_min,lightsleepduration,remsleepduration,rr_average,rr_max,rr_min,sleep_score,snoring,snoringepisodecount,wakeupcount,wakeupduration",
        }

        if start:
            params["startdateymd"] = start.strftime("%Y-%m-%d")
        if end:
            params["enddateymd"] = end.strftime("%Y-%m-%d")

        body = await self._api_call("/v2/sleep", params)
        series = body.get("series")
        return list(series) if isinstance(series, list) else []

    def _parse_measurement_value(self, measure: dict) -> float:
        """Parse Withings measurement value (value * 10^unit)"""
        value = float(measure.get("value", 0))
        unit = float(measure.get("unit", 0))
        return value * (10**unit)

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
            BodyComposition,
            HeartRateReading,
            SleepSession,
        )

        end = datetime.now(UTC)
        start = end - timedelta(days=days_back)

        counts: dict[str, int] = {
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
                    date_value = group.get("date", 0)
                    timestamp = datetime.fromtimestamp(
                        (
                            float(date_value)
                            if isinstance(date_value, (int, float, str))
                            else 0.0
                        ),
                        tz=UTC,
                    )

                    # Parse all measures in this group
                    measures: dict[str, float] = {}
                    group_measures = group.get("measures")
                    measures_list = (
                        list(group_measures) if isinstance(group_measures, list) else []
                    )
                    for m in measures_list:
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
                            water_pct=(
                                (measures.get("hydration") or 0)
                                / (measures.get("weight") or 1)
                                * 100
                                if measures.get("hydration") and measures.get("weight")
                                else None
                            ),
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
                            heart_rate_bpm=(
                                int(float(measures.get("heart_pulse", 0)))
                                if measures.get("heart_pulse") is not None
                                else 60
                            ),
                            activity_type="blood_pressure",
                        )
                        session.add(hr)
                        counts["blood_pressure"] += 1

                await session.commit()
                logger.info(
                    f"Synced {counts['weight']} weight, {counts['blood_pressure']} BP records from Withings"
                )
            except Exception as e:
                logger.error(f"Failed to sync Withings measurements: {e}")
                await session.rollback()

            # Sync sleep data
            try:
                sleep_records = await self.get_sleep(start, end)

                for record in sleep_records:
                    start_value = record.get("startdate", 0)
                    end_value = record.get("enddate", 0)
                    start_time = datetime.fromtimestamp(
                        (
                            float(start_value)
                            if isinstance(start_value, (int, float, str))
                            else 0.0
                        ),
                        tz=UTC,
                    )
                    end_time = datetime.fromtimestamp(
                        (
                            float(end_value)
                            if isinstance(end_value, (int, float, str))
                            else 0.0
                        ),
                        tz=UTC,
                    )

                    lightsleep = record.get("lightsleepduration", 0)
                    deepsleep = record.get("deepsleepduration", 0)
                    remsleep = record.get("remsleepduration", 0)
                    total_sleep = (
                        int(
                            (
                                float(lightsleep)
                                if isinstance(lightsleep, (int, float, str))
                                else 0.0
                            )
                            + (
                                float(deepsleep)
                                if isinstance(deepsleep, (int, float, str))
                                else 0.0
                            )
                            + (
                                float(remsleep)
                                if isinstance(remsleep, (int, float, str))
                                else 0.0
                            )
                        )
                        // 60
                    )  # Convert to minutes

                    sleep = SleepSession(
                        user_id=user_id,
                        device_id=device_id,
                        start_time=start_time,
                        end_time=end_time,
                        total_sleep_minutes=total_sleep,
                        time_in_bed_minutes=int(
                            (end_time - start_time).total_seconds() / 60
                        ),
                        deep_sleep_minutes=int(
                            (
                                float(deepsleep)
                                if isinstance(deepsleep, (int, float, str))
                                else 0.0
                            )
                            // 60
                        ),
                        rem_sleep_minutes=int(
                            (
                                float(remsleep)
                                if isinstance(remsleep, (int, float, str))
                                else 0.0
                            )
                            // 60
                        ),
                        light_sleep_minutes=int(
                            (
                                float(lightsleep)
                                if isinstance(lightsleep, (int, float, str))
                                else 0.0
                            )
                            // 60
                        ),
                        awake_minutes=int(
                            (
                                float(record.get("wakeupduration", 0))
                                if isinstance(
                                    record.get("wakeupduration", 0), (int, float, str)
                                )
                                else 0.0
                            )
                            // 60
                        ),
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
                    date_str = str(record.get("date", ""))
                    if not date_str:
                        continue

                    timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(
                        hour=12, tzinfo=UTC
                    )

                    # Store average HR if available
                    if record.get("hr_average"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=int(float(record.get("hr_average", 0))),
                            activity_type="daily_average",
                        )
                        session.add(hr)
                        counts["activity"] += 1

                await session.commit()
                logger.info(
                    f"Synced {counts['activity']} activity records from Withings"
                )
            except Exception as e:
                logger.error(f"Failed to sync Withings activity: {e}")
                await session.rollback()

        return counts
