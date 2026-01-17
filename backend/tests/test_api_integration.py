"""API integration tests

These tests require PostgreSQL with TimescaleDB. They are skipped when running
with SQLite (local development). In CI, the PostgreSQL service is available.
"""

import os
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

# Skip all tests in this module if not using PostgreSQL
pytestmark = pytest.mark.skipif(
    "postgresql" not in os.environ.get("DATABASE_URL", ""),
    reason="Integration tests require PostgreSQL",
)


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient):
    """Test complete authentication flow"""
    # Register
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "securepassword123",
            "first_name": "New",
            "last_name": "User",
        },
    )
    assert register_response.status_code == 200
    tokens = register_response.json()
    assert "access_token" in tokens

    # Get current user
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    user_response = await client.get("/api/v1/users/me", headers=headers)
    assert user_response.status_code == 200
    user = user_response.json()
    assert user["email"] == "newuser@test.com"


@pytest.mark.asyncio
async def test_health_data_crud(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
):
    """Test health data CRUD operations"""
    # Add heart rate reading
    reading_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "heart_rate_bpm": 72,
        "activity_type": "resting",
    }

    response = await client.post(
        "/api/v1/health/heart-rate",
        json=reading_data,
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Get heart rate data
    response = await client.get(
        "/api/v1/health/heart-rate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_analytics_endpoints(
    client: AsyncClient,
    auth_headers: dict,
    sample_heart_rate_data,
):
    """Test analytics endpoints"""
    # Get health score
    response = await client.get(
        "/api/v1/health/analytics/score",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Get trends
    response = await client.get(
        "/api/v1/health/analytics/trends?days=7",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clinical_endpoints(
    client: AsyncClient,
    auth_headers: dict,
    sample_heart_rate_data,
):
    """Test clinical integration endpoints"""
    # Get FHIR Patient
    response = await client.get(
        "/api/v1/clinical/fhir/Patient",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "Patient"

    # Generate physician report
    response = await client.get(
        "/api/v1/clinical/report?months=1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "executive_summary" in data


@pytest.mark.asyncio
async def test_hereditary_endpoints(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
):
    """Test hereditary health endpoints"""
    # Create family member
    response = await client.post(
        "/api/v1/hereditary/family",
        json={
            "relationship": "father",
            "name": "John Doe",
            "birth_year": 1950,
            "is_living": True,
            "conditions": [{"condition": "hypertension", "onset_age": 45}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    member = response.json()
    assert member["relationship"] == "father"

    # Get family members
    response = await client.get(
        "/api/v1/hereditary/family",
        headers=auth_headers,
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) >= 1

    # Get watchlist
    response = await client.get(
        "/api/v1/hereditary/watchlist",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Get risk assessment
    response = await client.get(
        "/api/v1/hereditary/risk",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "risks" in data


@pytest.mark.asyncio
async def test_device_endpoints(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
):
    """Test device management endpoints"""
    # List devices (should be empty initially)
    response = await client.get(
        "/api/v1/devices/",
        headers=auth_headers,
    )
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_alerts_endpoints(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
):
    """Test alerts endpoints"""
    # Get alerts
    response = await client.get(
        "/api/v1/alerts/",
        headers=auth_headers,
    )
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
