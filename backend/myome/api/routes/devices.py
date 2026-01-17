"""Device management routes"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.core.models import Device, DeviceType, DeviceVendor

router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceCreate(BaseModel):
    """Device creation request"""

    name: str
    device_type: DeviceType
    vendor: DeviceVendor
    model: str | None = None
    api_credentials: dict | None = None


class DeviceRead(BaseModel):
    """Device response"""

    id: str
    name: str
    device_type: str
    vendor: str
    model: str | None
    is_connected: bool
    last_sync_at: datetime | None

    model_config = {"from_attributes": True}


class DeviceSyncRequest(BaseModel):
    """Device sync request"""

    hours_back: int = 24


@router.get("/", response_model=list[DeviceRead])
async def list_devices(
    user: CurrentUser,
    session: DbSession,
) -> list[DeviceRead]:
    """List user's connected devices"""
    result = await session.execute(select(Device).where(Device.user_id == user.id))
    devices = result.scalars().all()
    return [DeviceRead.model_validate(d) for d in devices]


@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def add_device(
    device_data: DeviceCreate,
    user: CurrentUser,
    session: DbSession,
) -> DeviceRead:
    """Add a new device"""
    device = Device(
        user_id=user.id,
        name=device_data.name,
        device_type=device_data.device_type,
        vendor=device_data.vendor,
        model=device_data.model,
        api_credentials=device_data.api_credentials or {},
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)

    return DeviceRead.model_validate(device)


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(
    device_id: str,
    user: CurrentUser,
    session: DbSession,
) -> DeviceRead:
    """Get device details"""
    result = await session.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return DeviceRead.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    user: CurrentUser,
    session: DbSession,
) -> None:
    """Delete a device"""
    result = await session.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    await session.delete(device)
    await session.commit()


@router.post("/{device_id}/sync")
async def sync_device(
    device_id: str,
    sync_request: DeviceSyncRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Trigger device sync"""
    result = await session.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Trigger async sync via Celery
    from myome.sensors.tasks import sync_user_devices

    task = sync_user_devices.delay(user.id, sync_request.hours_back)

    # Update last sync time
    device.last_sync_at = datetime.now(UTC)
    await session.commit()

    return {
        "status": "sync_started",
        "task_id": task.id,
        "device_id": device_id,
    }
