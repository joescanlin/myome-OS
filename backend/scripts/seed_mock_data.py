#!/usr/bin/env python3
"""Seed mock data for testing the dashboard"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Add backend to path
sys.path.insert(0, '/Users/jscanlin/Documents/myome-OS/myome/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from myome.core.database import Base, engine
from myome.core.models import (
    User, HealthProfile, Device, 
    HeartRateReading, GlucoseReading, HRVReading, SleepSession
)
from myome.api.auth import get_password_hash


async def create_tables():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully")


async def seed_data():
    """Seed mock data"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Create test user
            user_id = str(uuid4())
            user = User(
                id=user_id,
                email="test@myome.health",
                hashed_password=get_password_hash("password123"),
                first_name="Test",
                last_name="User",
                is_active=True,
                timezone="America/New_York",
            )
            session.add(user)
            await session.flush()
            print(f"Created user: test@myome.health / password123")
            
            # Create health profile
            profile = HealthProfile(
                id=str(uuid4()),
                user_id=user_id,
                height_cm=175.0,
                baseline_weight_kg=70.0,
                exercise_frequency="moderate",
                diet_type="balanced",
                typical_sleep_hours=7.5,
            )
            session.add(profile)
            
            # Create device (using lowercase string values matching DB enum)
            device_id = str(uuid4())
            device = Device(
                id=device_id,
                user_id=user_id,
                name="Test Oura Ring",
                device_type="smart_ring",  # Must match DB enum value (lowercase)
                vendor="oura",  # Must match DB enum value (lowercase)
                model="Gen 3",
                is_connected=True,
                last_sync_at=datetime.now(timezone.utc),
            )
            session.add(device)
            
            # Generate 7 days of heart rate data (every 5 minutes)
            now = datetime.now(timezone.utc)
            print("Generating heart rate data...")
            for day in range(7):
                base_date = now - timedelta(days=day)
                for hour in range(24):
                    for minute in range(0, 60, 5):
                        timestamp = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        # Simulate circadian rhythm
                        if 0 <= hour < 6:
                            base_hr = 55  # Sleep
                        elif 6 <= hour < 9:
                            base_hr = 70  # Waking up
                        elif 9 <= hour < 17:
                            base_hr = 75  # Active day
                        elif 17 <= hour < 21:
                            base_hr = 80  # Evening activity
                        else:
                            base_hr = 65  # Winding down
                        
                        hr = HeartRateReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            heart_rate_bpm=base_hr + random.randint(-10, 15),
                            confidence=0.95,
                        )
                        session.add(hr)
            
            # Generate 7 days of glucose data (every 15 minutes for CGM)
            print("Generating glucose data...")
            for day in range(7):
                base_date = now - timedelta(days=day)
                for hour in range(24):
                    for minute in range(0, 60, 15):
                        timestamp = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        # Simulate meal spikes
                        if 7 <= hour < 9:  # Breakfast
                            base_glucose = 130
                        elif 12 <= hour < 14:  # Lunch
                            base_glucose = 140
                        elif 18 <= hour < 20:  # Dinner
                            base_glucose = 145
                        else:
                            base_glucose = 95  # Fasting
                        
                        glucose = GlucoseReading(
                            user_id=user_id,
                            device_id=device_id,
                            timestamp=timestamp,
                            glucose_mg_dl=base_glucose + random.randint(-15, 20),
                            trend="stable",
                        )
                        session.add(glucose)
            
            # Generate 7 days of HRV data (once per day, morning)
            print("Generating HRV data...")
            for day in range(7):
                timestamp = (now - timedelta(days=day)).replace(hour=7, minute=0, second=0, microsecond=0)
                hrv = HRVReading(
                    user_id=user_id,
                    device_id=device_id,
                    timestamp=timestamp,
                    sdnn_ms=45.0 + random.randint(-10, 15),
                    rmssd_ms=35.0 + random.randint(-8, 12),
                    pnn50_pct=20.0 + random.randint(-5, 10),
                )
                session.add(hrv)
            
            # Generate 7 days of sleep data
            print("Generating sleep data...")
            for day in range(7):
                start_time = (now - timedelta(days=day+1)).replace(hour=23, minute=0, second=0, microsecond=0)
                end_time = (now - timedelta(days=day)).replace(hour=7, minute=0, second=0, microsecond=0)
                total_minutes = 480 + random.randint(-60, 30)
                
                awake_minutes = random.randint(10, 30)
                time_in_bed = total_minutes + awake_minutes + random.randint(10, 20)  # Time in bed > total sleep
                
                sleep = SleepSession(
                    id=str(uuid4()),
                    user_id=user_id,
                    device_id=device_id,
                    start_time=start_time,
                    end_time=end_time,
                    total_sleep_minutes=total_minutes,
                    time_in_bed_minutes=time_in_bed,
                    deep_sleep_minutes=int(total_minutes * 0.2) + random.randint(-10, 10),
                    rem_sleep_minutes=int(total_minutes * 0.25) + random.randint(-10, 10),
                    light_sleep_minutes=int(total_minutes * 0.55),
                    awake_minutes=awake_minutes,
                    sleep_efficiency_pct=float(85 + random.randint(-5, 10)),
                    sleep_score=75 + random.randint(-10, 15),
                    avg_heart_rate_bpm=55 + random.randint(-5, 5),
                    avg_hrv_ms=float(40 + random.randint(-5, 10)),
                )
                session.add(sleep)
            
            await session.commit()
            print("\nMock data seeded successfully!")
            print(f"\nLogin credentials:")
            print(f"  Email: test@myome.health")
            print(f"  Password: password123")
            
        except Exception as e:
            await session.rollback()
            print(f"Error seeding data: {e}")
            raise


async def main():
    await create_tables()
    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
