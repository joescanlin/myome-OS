"""Oura Ring API adapter"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Optional

import httpx

from myome.core.logging import logger
from myome.sensors.base import (
    CalibrationParams,
    DataQuality,
    HealthSensor,
    Measurement,
    MultiSensorDevice,
    SensorMetadata,
    SensorType,
)
from myome.sensors.registry import SensorRegistry


class OuraAPIClient:
    """HTTP client for Oura API v2"""
    
    BASE_URL = "https://api.ouraring.com/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30.0,
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to Oura API"""
        response = await self._client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_sleep(self, start_date: str, end_date: str) -> list[dict]:
        """Get sleep data for date range"""
        data = await self.get(
            "/usercollection/sleep",
            params={"start_date": start_date, "end_date": end_date}
        )
        return data.get("data", [])
    
    async def get_heart_rate(self, start_date: str, end_date: str) -> list[dict]:
        """Get heart rate data"""
        data = await self.get(
            "/usercollection/heartrate",
            params={"start_date": start_date, "end_date": end_date}
        )
        return data.get("data", [])
    
    async def get_daily_activity(self, start_date: str, end_date: str) -> list[dict]:
        """Get daily activity data"""
        data = await self.get(
            "/usercollection/daily_activity",
            params={"start_date": start_date, "end_date": end_date}
        )
        return data.get("data", [])


class OuraHeartRateSensor(HealthSensor):
    """Oura Ring heart rate sensor"""
    
    def __init__(self, access_token: str, device_id: str = "oura"):
        self._access_token = access_token
        self._device_id = device_id
        self._client: Optional[OuraAPIClient] = None
        self._metadata = SensorMetadata(
            vendor="oura",
            model="Oura Ring Gen 3",
        )
        self._calibration = CalibrationParams()
    
    @property
    def sensor_id(self) -> str:
        return f"oura:{self._device_id}:heart_rate"
    
    @property
    def sensor_type(self) -> SensorType:
        return SensorType.HEART_RATE
    
    @property
    def metadata(self) -> SensorMetadata:
        return self._metadata
    
    async def connect(self) -> None:
        self._client = OuraAPIClient(self._access_token)
        await self._client.__aenter__()
        logger.info(f"Connected to Oura API for {self.sensor_id}")
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
    
    async def is_connected(self) -> bool:
        return self._client is not None
    
    async def stream_data(self) -> AsyncIterator[Measurement]:
        """Oura doesn't support real-time streaming, poll periodically"""
        while True:
            # Get last hour of data
            end = datetime.utcnow()
            start = end - timedelta(hours=1)
            
            measurements = await self.get_historical(start, end)
            for m in measurements:
                yield m
            
            # Poll every 5 minutes
            await asyncio.sleep(300)
    
    async def get_historical(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]:
        """Get historical heart rate data"""
        if not self._client:
            raise RuntimeError("Sensor not connected")
        
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        
        raw_data = await self._client.get_heart_rate(start_str, end_str)
        
        measurements = []
        for reading in raw_data:
            timestamp = datetime.fromisoformat(reading["timestamp"].replace("Z", "+00:00"))
            
            # Skip if outside requested range
            if timestamp < start or timestamp > end:
                continue
            
            bpm = reading.get("bpm")
            if bpm is None:
                continue
            
            # Apply calibration
            calibrated_bpm = self._calibration.apply(bpm)
            
            measurements.append(Measurement(
                timestamp=timestamp,
                value=calibrated_bpm,
                unit="bpm",
                sensor_type=SensorType.HEART_RATE,
                confidence=0.9,  # Oura uses PPG, generally reliable
                quality=DataQuality.MEDIUM,
                metadata={
                    "source": reading.get("source", "unknown"),
                    "raw_value": bpm,
                }
            ))
        
        return measurements
    
    def get_calibration(self) -> CalibrationParams:
        return self._calibration
    
    def set_calibration(self, params: CalibrationParams) -> None:
        self._calibration = params


class OuraSleepSensor(HealthSensor):
    """Oura Ring sleep sensor"""
    
    def __init__(self, access_token: str, device_id: str = "oura"):
        self._access_token = access_token
        self._device_id = device_id
        self._client: Optional[OuraAPIClient] = None
        self._metadata = SensorMetadata(
            vendor="oura",
            model="Oura Ring Gen 3",
        )
    
    @property
    def sensor_id(self) -> str:
        return f"oura:{self._device_id}:sleep"
    
    @property
    def sensor_type(self) -> SensorType:
        return SensorType.SLEEP
    
    @property
    def metadata(self) -> SensorMetadata:
        return self._metadata
    
    async def connect(self) -> None:
        self._client = OuraAPIClient(self._access_token)
        await self._client.__aenter__()
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
    
    async def is_connected(self) -> bool:
        return self._client is not None
    
    async def stream_data(self) -> AsyncIterator[Measurement]:
        """Sleep data is batch, not streaming"""
        raise NotImplementedError("Sleep data doesn't support streaming")
    
    async def get_historical(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Measurement]:
        """Get historical sleep sessions"""
        if not self._client:
            raise RuntimeError("Sensor not connected")
        
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        
        raw_data = await self._client.get_sleep(start_str, end_str)
        
        measurements = []
        for session in raw_data:
            # Parse session timing
            bedtime = datetime.fromisoformat(
                session["bedtime_start"].replace("Z", "+00:00")
            )
            
            # Create measurement with sleep session data
            measurements.append(Measurement(
                timestamp=bedtime,
                value=session.get("total_sleep_duration", 0) / 60,  # Convert to minutes
                unit="minutes",
                sensor_type=SensorType.SLEEP,
                confidence=0.85,
                quality=DataQuality.MEDIUM,
                metadata={
                    "type": session.get("type", "long_sleep"),
                    "bedtime_start": session.get("bedtime_start"),
                    "bedtime_end": session.get("bedtime_end"),
                    "deep_sleep_duration": session.get("deep_sleep_duration"),
                    "light_sleep_duration": session.get("light_sleep_duration"),
                    "rem_sleep_duration": session.get("rem_sleep_duration"),
                    "awake_time": session.get("awake_time"),
                    "sleep_efficiency": session.get("efficiency"),
                    "latency": session.get("latency"),
                    "average_heart_rate": session.get("average_heart_rate"),
                    "lowest_heart_rate": session.get("lowest_heart_rate"),
                    "average_hrv": session.get("average_hrv"),
                    "respiratory_rate": session.get("average_breath"),
                    "sleep_score": session.get("score"),
                }
            ))
        
        return measurements


@SensorRegistry.register_device("oura")
class OuraDevice(MultiSensorDevice):
    """Oura Ring multi-sensor device"""
    
    def __init__(self, access_token: str, device_id: str = "oura"):
        self._access_token = access_token
        self._device_id = device_id
        self._sensors: dict[SensorType, HealthSensor] = {}
    
    @property
    def device_id(self) -> str:
        return self._device_id
    
    @property
    def supported_sensors(self) -> list[SensorType]:
        return [
            SensorType.HEART_RATE,
            SensorType.HRV,
            SensorType.SLEEP,
            SensorType.ACTIVITY,
            SensorType.BODY_COMPOSITION,  # Body temperature trends
        ]
    
    def get_sensor(self, sensor_type: SensorType) -> Optional[HealthSensor]:
        if sensor_type not in self._sensors:
            if sensor_type == SensorType.HEART_RATE:
                self._sensors[sensor_type] = OuraHeartRateSensor(
                    self._access_token, self._device_id
                )
            elif sensor_type == SensorType.SLEEP:
                self._sensors[sensor_type] = OuraSleepSensor(
                    self._access_token, self._device_id
                )
            # Add more sensor types as needed
        
        return self._sensors.get(sensor_type)
    
    async def sync_all(
        self,
        start: datetime,
        end: datetime,
    ) -> dict[SensorType, list[Measurement]]:
        """Sync all available sensors"""
        results = {}
        
        for sensor_type in self.supported_sensors:
            sensor = self.get_sensor(sensor_type)
            if sensor:
                try:
                    await sensor.connect()
                    measurements = await sensor.get_historical(start, end)
                    results[sensor_type] = measurements
                except Exception as e:
                    logger.error(f"Error syncing {sensor_type}: {e}")
                    results[sensor_type] = []
                finally:
                    await sensor.disconnect()
        
        return results
