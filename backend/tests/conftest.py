"""Pytest configuration and fixtures"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from myome.api.main import app
from myome.core.database import Base, get_session
from myome.core.models import User, HeartRateReading


# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_myome.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_user(session: AsyncSession) -> User:
    """Create test user"""
    from myome.api.auth import get_password_hash
    
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Get auth headers for test user"""
    from myome.api.auth import create_token_pair
    
    tokens = create_token_pair(test_user.id)
    return {"Authorization": f"Bearer {tokens.access_token}"}


@pytest_asyncio.fixture(scope="function")
async def sample_heart_rate_data(session: AsyncSession, test_user: User):
    """Create sample heart rate data"""
    readings = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)
    
    for i in range(100):
        reading = HeartRateReading(
            timestamp=base_time + timedelta(hours=i),
            user_id=test_user.id,
            heart_rate_bpm=60 + (i % 40),
            confidence=0.95,
        )
        readings.append(reading)
    
    session.add_all(readings)
    await session.commit()
    return readings


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    
    async def override_get_session():
        yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
