"""Dexcom CGM API adapter"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import httpx

from myome.core.logging import logger
from myome.sensors.base import (
    CalibrationParams,
    DataQuality,
    HealthSensor,
    Measurement,
    SensorMetadata,
    SensorType,
)
from myome.sensors.registry import SensorRegistry


class DexcomAPIClient:
    """HTTP client for Dexcom API"""

    # Dexcom uses different base URLs for different regions
    BASE_URL_US = "https://api.dexcom.com"
    BASE_URL_OUS = "https://api.dexcom.eu"  # Outside US

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
        region: str = "us",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.base_url = self.BASE_URL_US if region == "us" else self.BASE_URL_OUS
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def get_egvs(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get estimated glucose values (EGVs)

        Note: Dexcom uses specific date format and returns max 90 days
        """
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")

        response = await self._client.get(
            "/v3/users/self/egvs",
            params={
                "startDate": start_str,
                "endDate": end_str,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("records", [])

    async def get_calibrations(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """Get calibration records"""
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")

        response = await self._client.get(
            "/v3/users/self/calibrations",
            params={
                "startDate": start_str,
                "endDate": end_str,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("records", [])


@SensorRegistry.register("dexcom", SensorType.GLUCOSE)
class DexcomGlucoseSensor(HealthSensor):
    """Dexcom CGM glucose sensor"""

    # Dexcom trend arrows mapping
    TREND_ARROWS = {
        "none": None,
        "doubleUp": "rising_rapidly",
        "singleUp": "rising",
        "fortyFiveUp": "rising_slowly",
        "flat": "stable",
        "fortyFiveDown": "falling_slowly",
        "singleDown": "falling",
        "doubleDown": "falling_rapidly",
        "notComputable": None,
        "rateOutOfRange": None,
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
        region: str = "us",
        device_id: str = "dexcom",
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._region = region
        self._device_id = device_id
        self._client: DexcomAPIClient | None = None
        self._metadata = SensorMetadata(
            vendor="dexcom",
            model="G6/G7",
        )
        self._calibration = CalibrationParams(
            lag_seconds=900,  # ~15 minute interstitial lag
        )

    @property
    def sensor_id(self) -> str:
        return f"dexcom:{self._device_id}:glucose"

    @property
    def sensor_type(self) -> SensorType:
        return SensorType.GLUCOSE

    @property
    def metadata(self) -> SensorMetadata:
        return self._metadata

    async def connect(self) -> None:
        self._client = DexcomAPIClient(
            self._client_id,
            self._client_secret,
            self._access_token,
            self._refresh_token,
            self._region,
        )
        await self._client.__aenter__()
        logger.info(f"Connected to Dexcom API for {self.sensor_id}")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def is_connected(self) -> bool:
        return self._client is not None

    async def stream_data(self) -> AsyncIterator[Measurement]:
        """Stream glucose readings (poll every 5 minutes to match CGM cadence)"""
        last_timestamp = datetime.utcnow() - timedelta(hours=1)

        while True:
            end = datetime.utcnow()

            measurements = await self.get_historical(last_timestamp, end)

            for m in measurements:
                if m.timestamp > last_timestamp:
                    yield m
                    last_timestamp = m.timestamp

            # Dexcom updates every 5 minutes
            await asyncio.sleep(300)

    async def get_historical(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]:
        """Get historical glucose readings"""
        if not self._client:
            raise RuntimeError("Sensor not connected")

        raw_data = await self._client.get_egvs(start, end)

        measurements = []
        for reading in raw_data:
            # Parse timestamp
            timestamp = datetime.fromisoformat(
                reading["systemTime"].replace("Z", "+00:00")
            )

            # Get glucose value
            glucose_mg_dl = reading.get("value")
            if glucose_mg_dl is None:
                continue

            # Apply calibration (mainly lag compensation)
            calibrated_value = self._calibration.apply(glucose_mg_dl)

            # Determine quality based on Dexcom's quality indicators
            quality = DataQuality.HIGH  # Dexcom is FDA-approved
            if reading.get("status") != "active":
                quality = DataQuality.LOW

            # Map trend arrow
            trend_direction = reading.get("trendDirection", "none")
            trend = self.TREND_ARROWS.get(trend_direction)

            measurements.append(
                Measurement(
                    timestamp=timestamp,
                    value=calibrated_value,
                    unit="mg/dL",
                    sensor_type=SensorType.GLUCOSE,
                    confidence=0.92,  # Dexcom G6 MARD ~9%
                    quality=quality,
                    metadata={
                        "trend": trend,
                        "trend_rate": reading.get("trendRate"),
                        "raw_value": glucose_mg_dl,
                        "transmitter_id": reading.get("transmitterId"),
                        "display_time": reading.get("displayTime"),
                    },
                )
            )

        return sorted(measurements, key=lambda m: m.timestamp)

    def get_calibration(self) -> CalibrationParams:
        return self._calibration

    def set_calibration(self, params: CalibrationParams) -> None:
        self._calibration = params
