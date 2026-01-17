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

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def ensure_valid_token(self) -> OAuthTokens:
        """Refresh token if expired"""
        if self.tokens.is_expired():
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

    async def get_user_profile(self) -> dict:
        """Get basic user profile"""
        await self.ensure_valid_token()
        response = await self.client.get("/v2/user/profile/basic")
        response.raise_for_status()
        return response.json()

    async def get_body_measurements(self) -> dict:
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
    ) -> list[dict]:
        """Get sleep sessions"""
        await self.ensure_valid_token()

        params = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/activity/sleep", params=params)
            response.raise_for_status()
            data = response.json()

            all_records.extend(data.get("records", []))
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_recovery_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Get recovery data (HRV, resting HR, etc)"""
        await self.ensure_valid_token()

        params = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/recovery", params=params)
            response.raise_for_status()
            data = response.json()

            all_records.extend(data.get("records", []))
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_workout_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Get workout data"""
        await self.ensure_valid_token()

        params = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/activity/workout", params=params)
            response.raise_for_status()
            data = response.json()

            all_records.extend(data.get("records", []))
            next_token = data.get("next_token")

            if not next_token or len(all_records) >= limit:
                break

        return all_records[:limit]

    async def get_cycle_collection(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """Get daily cycle data (strain)"""
        await self.ensure_valid_token()

        params = {"limit": min(limit, 25)}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        all_records = []
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token

            response = await self.client.get("/v2/cycle", params=params)
            response.raise_for_status()
            data = response.json()

            all_records.extend(data.get("records", []))
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

        counts = {
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

                    score = record.get("score", {})
                    stage = score.get("stage_summary", {})

                    sleep = SleepSession(
                        user_id=user_id,
                        device_id=device_id,
                        start_time=datetime.fromisoformat(
                            record["start"].replace("Z", "+00:00")
                        ),
                        end_time=datetime.fromisoformat(
                            record["end"].replace("Z", "+00:00")
                        ),
                        total_sleep_minutes=int(
                            stage.get("total_in_bed_time_milli", 0) / 60000
                        ),
                        time_in_bed_minutes=int(
                            stage.get("total_in_bed_time_milli", 0) / 60000
                        ),
                        deep_sleep_minutes=int(
                            stage.get("total_slow_wave_sleep_time_milli", 0) / 60000
                        ),
                        rem_sleep_minutes=int(
                            stage.get("total_rem_sleep_time_milli", 0) / 60000
                        ),
                        light_sleep_minutes=int(
                            stage.get("total_light_sleep_time_milli", 0) / 60000
                        ),
                        awake_minutes=int(
                            stage.get("total_awake_time_milli", 0) / 60000
                        ),
                        sleep_efficiency_pct=score.get("sleep_efficiency_percentage"),
                        sleep_score=int(score.get("sleep_performance_percentage", 0)),
                        avg_respiratory_rate=score.get("respiratory_rate"),
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

                    score = record.get("score", {})
                    timestamp = datetime.fromisoformat(
                        record["created_at"].replace("Z", "+00:00")
                    )

                    # HRV reading
                    if score.get("hrv_rmssd_milli"):
                        hrv = HRVReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            rmssd_ms=score["hrv_rmssd_milli"],
                        )
                        session.add(hrv)

                    # Resting heart rate
                    if score.get("resting_heart_rate"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=score["resting_heart_rate"],
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

                    score = record.get("score", {})
                    timestamp = datetime.fromisoformat(
                        record["start"].replace("Z", "+00:00")
                    )

                    # Average HR during workout
                    if score.get("average_heart_rate"):
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=score["average_heart_rate"],
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
