"""Whoop data sync service"""

from datetime import UTC, datetime, timedelta

import httpx

from myome.core.config import settings
from myome.core.logging import logger
from myome.integrations.oauth import OAuthTokens, WhoopOAuth


class WhoopSyncService:
    """Service to sync data from Whoop API"""

    BASE_URL = "https://api.prod.whoop.com/developer"

    def __init__(self, tokens: OAuthTokens):
        self.tokens = tokens
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.tokens.access_token}",
                },
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
                raise ValueError("Whoop refresh token missing")
            oauth = WhoopOAuth(
                client_id=settings.whoop_client_id,
                client_secret=settings.whoop_client_secret,
                redirect_uri=settings.whoop_redirect_uri,
            )
            try:
                self.tokens = await oauth.refresh_tokens(self.tokens.refresh_token)
                # Update client with new token
                if self._client:
                    self._client.headers["Authorization"] = (
                        f"Bearer {self.tokens.access_token}"
                    )
            finally:
                await oauth.close()
        return self.tokens

    async def get_user_profile(self) -> dict[str, object]:
        """Get basic user profile"""
        await self.ensure_valid_token()
        response = await self.client.get("/v2/user/profile/basic")
        response.raise_for_status()
        return response.json()

    async def get_body_measurements(self) -> dict[str, object]:
        """Get body measurements (height, weight, max HR)"""
        await self.ensure_valid_token()
        response = await self.client.get("/v2/user/measurement/body")
        response.raise_for_status()
        return response.json()

    async def get_sleep_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict[str, object]]:
        """Get sleep sessions"""
        await self.ensure_valid_token()

        params: dict[str, str | int] = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records: list[dict[str, object]] = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/activity/sleep", params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get("records")
            all_records.extend(list(records) if isinstance(records, list) else [])
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_recovery_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict[str, object]]:
        """Get recovery data (HRV, resting HR, etc)"""
        await self.ensure_valid_token()

        params: dict[str, str | int] = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records: list[dict[str, object]] = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/recovery", params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get("records")
            all_records.extend(list(records) if isinstance(records, list) else [])
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_workout_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict[str, object]]:
        """Get workout data"""
        await self.ensure_valid_token()

        params: dict[str, str | int] = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records: list[dict[str, object]] = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/activity/workout", params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get("records")
            all_records.extend(list(records) if isinstance(records, list) else [])
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_cycle_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict[str, object]]:
        """Get daily cycle data (strain)"""
        await self.ensure_valid_token()

        params: dict[str, str | int] = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records: list[dict[str, object]] = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/cycle", params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get("records")
            all_records.extend(list(records) if isinstance(records, list) else [])
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def sync_all_data(
        self,
        user_id: str,
        device_id: str,
        days_back: int = 7,
    ) -> dict:
        """
        Sync all Whoop data to Myome database.
        Returns count of records synced per type.
        """
        from myome.core.database import async_session_factory
        from myome.core.models import (
            HeartRateReading,
            HRVReading,
            SleepSession,
        )

        end = datetime.now(UTC)
        start = end - timedelta(days=days_back)

        counts: dict[str, int] = {
            "sleep": 0,
            "recovery": 0,
            "workout": 0,
        }

        async with async_session_factory() as session:
            # Sync sleep data
            try:
                sleep_records = await self.get_sleep_collection(start, end, limit=100)
                for record in sleep_records:
                    if record.get("score_state") != "SCORED":
                        continue

                    score = record.get("score")
                    score_dict = score if isinstance(score, dict) else {}
                    stage = score_dict.get("stage_summary")
                    stage_dict = stage if isinstance(stage, dict) else {}

                    start_str = str(record.get("start", ""))
                    end_str = str(record.get("end", ""))
                    if not start_str or not end_str:
                        continue

                    sleep = SleepSession(
                        user_id=user_id,
                        device_id=device_id,
                        start_time=datetime.fromisoformat(
                            start_str.replace("Z", "+00:00")
                        ),
                        end_time=datetime.fromisoformat(end_str.replace("Z", "+00:00")),
                        total_sleep_minutes=int(
                            float(stage_dict.get("total_in_bed_time_milli", 0)) / 60000
                        ),
                        time_in_bed_minutes=int(
                            float(stage_dict.get("total_in_bed_time_milli", 0)) / 60000
                        ),
                        deep_sleep_minutes=int(
                            float(stage_dict.get("total_slow_wave_sleep_time_milli", 0))
                            / 60000
                        ),
                        rem_sleep_minutes=int(
                            float(stage_dict.get("total_rem_sleep_time_milli", 0))
                            / 60000
                        ),
                        light_sleep_minutes=int(
                            float(stage_dict.get("total_light_sleep_time_milli", 0))
                            / 60000
                        ),
                        awake_minutes=int(
                            float(stage_dict.get("total_awake_time_milli", 0)) / 60000
                        ),
                        sleep_efficiency_pct=score_dict.get(
                            "sleep_efficiency_percentage"
                        ),
                        sleep_score=int(
                            float(score_dict.get("sleep_performance_percentage", 0))
                        ),
                        avg_respiratory_rate=score_dict.get("respiratory_rate"),
                    )
                    session.add(sleep)
                    counts["sleep"] += 1

                await session.commit()
                logger.info(f"Synced {counts['sleep']} sleep records from Whoop")
            except Exception as e:
                logger.error(f"Failed to sync Whoop sleep: {e}")
                await session.rollback()

            # Sync recovery data (HRV, resting HR)
            try:
                recovery_records = await self.get_recovery_collection(
                    start, end, limit=100
                )
                for record in recovery_records:
                    if record.get("score_state") != "SCORED":
                        continue

                    score = record.get("score")
                    score_dict = score if isinstance(score, dict) else {}
                    created_at = str(record.get("created_at", ""))
                    if not created_at:
                        continue
                    timestamp = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )

                    # HRV reading
                    if score_dict.get("hrv_rmssd_milli"):
                        hrv = HRVReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            rmssd_ms=float(score_dict.get("hrv_rmssd_milli", 0)),
                        )
                        session.add(hrv)

                    # Resting heart rate
                    if score_dict.get("resting_heart_rate"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=int(
                                float(score_dict.get("resting_heart_rate", 0))
                            ),
                            activity_type="resting",
                        )
                        session.add(hr)

                    counts["recovery"] += 1

                await session.commit()
                logger.info(f"Synced {counts['recovery']} recovery records from Whoop")
            except Exception as e:
                logger.error(f"Failed to sync Whoop recovery: {e}")
                await session.rollback()

            # Sync workout data
            try:
                workout_records = await self.get_workout_collection(
                    start, end, limit=100
                )
                for record in workout_records:
                    if record.get("score_state") != "SCORED":
                        continue

                    score = record.get("score")
                    score_dict = score if isinstance(score, dict) else {}
                    start_time = str(record.get("start", ""))
                    if not start_time:
                        continue
                    timestamp = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    )

                    # Average HR during workout
                    if score_dict.get("average_heart_rate"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=int(
                                float(score_dict.get("average_heart_rate", 0))
                            ),
                            activity_type=record.get("sport_name", "workout"),
                        )
                        session.add(hr)

                    counts["workout"] += 1

                await session.commit()
                logger.info(f"Synced {counts['workout']} workout records from Whoop")
            except Exception as e:
                logger.error(f"Failed to sync Whoop workouts: {e}")
                await session.rollback()

        return counts
