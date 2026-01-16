"""Data ingestion service for coordinating sensor data collection"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from myome.core.database import get_session_context
from myome.core.logging import logger
from myome.core.models import (
    GlucoseReading,
    HeartRateReading,
    HRVReading,
)
from myome.sensors.base import HealthSensor, Measurement, MultiSensorDevice, SensorType
from myome.sensors.normalizer import DataNormalizer


class IngestionService:
    """
    Coordinates data ingestion from multiple sensors
    
    Handles:
    - Periodic sync of historical data
    - Real-time streaming where supported
    - Data normalization and validation
    - Storage to database
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.normalizer = DataNormalizer()
        self._devices: dict[str, MultiSensorDevice] = {}
        self._sensors: dict[str, HealthSensor] = {}
        self._running = False
    
    def add_device(self, device_id: str, device: MultiSensorDevice) -> None:
        """Register a device for data collection"""
        self._devices[device_id] = device
        logger.info(f"Added device {device_id} for user {self.user_id}")
    
    def add_sensor(self, sensor_id: str, sensor: HealthSensor) -> None:
        """Register a standalone sensor for data collection"""
        self._sensors[sensor_id] = sensor
        logger.info(f"Added sensor {sensor_id} for user {self.user_id}")
    
    async def sync_device(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
    ) -> dict[SensorType, int]:
        """
        Sync all data from a device for a time range
        
        Returns dict of sensor_type -> measurement count
        """
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        results = await device.sync_all(start, end)
        counts = {}
        
        for sensor_type, measurements in results.items():
            # Normalize measurements
            normalized = []
            for m in measurements:
                norm = self.normalizer.normalize(m)
                if norm:
                    normalized.append(norm)
            
            # Store to database
            count = await self._store_measurements(sensor_type, normalized)
            counts[sensor_type] = count
            
            logger.info(
                f"Synced {count} {sensor_type.value} measurements "
                f"from {device_id} for user {self.user_id}"
            )
        
        return counts
    
    async def sync_all_devices(
        self,
        start: datetime,
        end: datetime,
    ) -> dict[str, dict[SensorType, int]]:
        """Sync all registered devices"""
        results = {}
        
        for device_id in self._devices:
            try:
                counts = await self.sync_device(device_id, start, end)
                results[device_id] = counts
            except Exception as e:
                logger.error(f"Error syncing device {device_id}: {e}")
                results[device_id] = {}
        
        return results
    
    async def _store_measurements(
        self,
        sensor_type: SensorType,
        measurements: list[Measurement],
    ) -> int:
        """Store measurements to database"""
        if not measurements:
            return 0
        
        async with get_session_context() as session:
            count = 0
            
            for m in measurements:
                try:
                    if sensor_type == SensorType.HEART_RATE:
                        await self._store_heart_rate(session, m)
                    elif sensor_type == SensorType.GLUCOSE:
                        await self._store_glucose(session, m)
                    elif sensor_type == SensorType.HRV:
                        await self._store_hrv(session, m)
                    # Add more sensor types as needed
                    
                    count += 1
                except Exception as e:
                    logger.error(f"Error storing measurement: {e}")
            
            await session.commit()
        
        return count
    
    async def _store_heart_rate(
        self,
        session: AsyncSession,
        measurement: Measurement,
    ) -> None:
        """Store heart rate reading"""
        reading = HeartRateReading(
            timestamp=measurement.timestamp,
            user_id=self.user_id,
            heart_rate_bpm=int(measurement.value),
            device_id=measurement.metadata.get("device_id"),
            activity_type=measurement.metadata.get("activity_type"),
            confidence=measurement.confidence,
        )
        session.add(reading)
    
    async def _store_glucose(
        self,
        session: AsyncSession,
        measurement: Measurement,
    ) -> None:
        """Store glucose reading"""
        reading = GlucoseReading(
            timestamp=measurement.timestamp,
            user_id=self.user_id,
            glucose_mg_dl=measurement.value,
            trend=measurement.metadata.get("trend"),
            trend_rate=measurement.metadata.get("trend_rate"),
            is_calibrated=measurement.metadata.get("is_calibrated", True),
            device_id=measurement.metadata.get("device_id"),
            meal_context=measurement.metadata.get("meal_context"),
        )
        session.add(reading)
    
    async def _store_hrv(
        self,
        session: AsyncSession,
        measurement: Measurement,
    ) -> None:
        """Store HRV reading"""
        reading = HRVReading(
            timestamp=measurement.timestamp,
            user_id=self.user_id,
            sdnn_ms=measurement.metadata.get("sdnn"),
            rmssd_ms=measurement.value if measurement.unit == "ms" else None,
            pnn50_pct=measurement.metadata.get("pnn50"),
            lf_power=measurement.metadata.get("lf_power"),
            hf_power=measurement.metadata.get("hf_power"),
            lf_hf_ratio=measurement.metadata.get("lf_hf_ratio"),
            device_id=measurement.metadata.get("device_id"),
        )
        session.add(reading)
    
    async def start_streaming(self) -> None:
        """Start real-time data streaming from all sensors that support it"""
        self._running = True
        
        tasks = []
        for sensor_id, sensor in self._sensors.items():
            tasks.append(self._stream_sensor(sensor_id, sensor))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def stop_streaming(self) -> None:
        """Stop all streaming"""
        self._running = False
    
    async def _stream_sensor(self, sensor_id: str, sensor: HealthSensor) -> None:
        """Stream data from a single sensor"""
        try:
            await sensor.connect()
            
            async for measurement in sensor.stream_data():
                if not self._running:
                    break
                
                normalized = self.normalizer.normalize(measurement)
                if normalized:
                    await self._store_measurements(
                        sensor.sensor_type,
                        [normalized]
                    )
        
        except NotImplementedError:
            logger.debug(f"Sensor {sensor_id} doesn't support streaming")
        except Exception as e:
            logger.error(f"Error streaming from {sensor_id}: {e}")
        finally:
            await sensor.disconnect()
