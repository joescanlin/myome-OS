"""Celery tasks for device integration and data sync"""

import asyncio
from collections.abc import Awaitable
from datetime import UTC, datetime

from myome.core.celery_app import celery_app
from myome.core.logging import logger


def run_async(coro: Awaitable[dict]) -> dict:
    """Run async code in sync context"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="myome.integrations.tasks.sync_device")
def sync_device(device_id: str) -> dict:
    """
    Sync data from a single device.
    Called when a device is first connected or manually triggered.
    """

    async def _sync():
        from sqlalchemy import select

        from myome.core.database import async_session_factory
        from myome.core.models import Device
        from myome.integrations.oauth import OAuthTokens
        from myome.integrations.sync import WhoopSyncService, WithingsSyncService

        async with async_session_factory() as session:
            result = await session.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()

            if not device:
                logger.error(f"Device {device_id} not found")
                return {"error": "Device not found"}

            if not device.is_connected or not device.api_credentials:
                logger.warning(
                    f"Device {device_id} is not connected or has no credentials"
                )
                return {"error": "Device not connected"}

            tokens = OAuthTokens.from_dict(device.api_credentials)

            try:
                if device.vendor == "whoop":
                    sync_service = WhoopSyncService(tokens)
                    counts = await sync_service.sync_all_data(
                        user_id=device.user_id,
                        device_id=device.id,
                        days_back=7,
                    )
                    # Update tokens if refreshed
                    device.api_credentials = sync_service.tokens.to_dict()
                    await sync_service.close()

                elif device.vendor == "withings":
                    sync_service = WithingsSyncService(tokens)
                    counts = await sync_service.sync_all_data(
                        user_id=device.user_id,
                        device_id=device.id,
                        days_back=30,
                    )
                    # Update tokens if refreshed
                    device.api_credentials = sync_service.tokens.to_dict()
                    await sync_service.close()

                else:
                    logger.warning(f"Unknown vendor: {device.vendor}")
                    return {"error": f"Unknown vendor: {device.vendor}"}

                device.last_sync_at = datetime.now(UTC)
                await session.commit()

                logger.info(f"Synced device {device_id}: {counts}")
                return {"status": "success", "counts": counts}

            except Exception as e:
                logger.error(f"Failed to sync device {device_id}: {e}")
                device.is_connected = False
                await session.commit()
                return {"error": str(e)}

    return run_async(_sync())


@celery_app.task(name="myome.integrations.tasks.sync_all_devices")
def sync_all_devices() -> dict:
    """
    Sync all connected devices for all users.
    Called periodically by Celery Beat.
    """

    async def _sync_all():
        from sqlalchemy import select

        from myome.core.database import async_session_factory
        from myome.core.models import Device

        async with async_session_factory() as session:
            result = await session.execute(
                select(Device).where(
                    Device.is_connected,
                    Device.api_credentials.isnot(None),
                )
            )
            devices = result.scalars().all()

            logger.info(f"Found {len(devices)} connected devices to sync")

            results = {}
            for device in devices:
                # Queue individual sync tasks
                sync_device.delay(device.id)
                results[device.id] = "queued"

            return {
                "devices_queued": len(devices),
                "results": results,
            }

    return run_async(_sync_all())


@celery_app.task(name="myome.integrations.tasks.run_daily_analytics")
def run_daily_analytics() -> dict:
    """
    Run daily analytics for all users.
    Called daily at 3 AM by Celery Beat.
    """

    async def _run_analytics():
        from sqlalchemy import select

        from myome.analytics.service import AnalyticsService
        from myome.core.database import async_session_factory
        from myome.core.models import User

        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.is_active))
            users = result.scalars().all()

            logger.info(f"Running daily analytics for {len(users)} users")

            results = {}
            for user in users:
                try:
                    service = AnalyticsService(user.id)
                    analysis = await service.run_daily_analysis()
                    results[user.id] = {
                        "status": "success",
                        "health_score": analysis.get("health_score"),
                        "alerts": len(analysis.get("alerts", [])),
                    }
                except Exception as e:
                    logger.error(f"Analytics failed for user {user.id}: {e}")
                    results[user.id] = {"status": "error", "error": str(e)}

            return {
                "users_processed": len(users),
                "results": results,
            }

    return run_async(_run_analytics())


@celery_app.task(name="myome.integrations.tasks.initial_device_sync")
def initial_device_sync(device_id: str) -> dict:
    """
    Perform initial sync when a device is first connected.
    Syncs more historical data than regular sync.
    """

    async def _initial_sync():
        from sqlalchemy import select

        from myome.core.database import async_session_factory
        from myome.core.models import Device
        from myome.integrations.oauth import OAuthTokens
        from myome.integrations.sync import WhoopSyncService, WithingsSyncService

        async with async_session_factory() as session:
            result = await session.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()

            if not device or not device.api_credentials:
                return {"error": "Device not found or not connected"}

            tokens = OAuthTokens.from_dict(device.api_credentials)

            try:
                if device.vendor == "whoop":
                    sync_service = WhoopSyncService(tokens)
                    counts = await sync_service.sync_all_data(
                        user_id=device.user_id,
                        device_id=device.id,
                        days_back=30,  # More history on initial sync
                    )
                    device.api_credentials = sync_service.tokens.to_dict()
                    await sync_service.close()

                elif device.vendor == "withings":
                    sync_service = WithingsSyncService(tokens)
                    counts = await sync_service.sync_all_data(
                        user_id=device.user_id,
                        device_id=device.id,
                        days_back=90,  # More history on initial sync
                    )
                    device.api_credentials = sync_service.tokens.to_dict()
                    await sync_service.close()

                else:
                    return {"error": f"Unknown vendor: {device.vendor}"}

                device.last_sync_at = datetime.now(UTC)
                await session.commit()

                logger.info(f"Initial sync for device {device_id} complete: {counts}")
                return {"status": "success", "counts": counts}

            except Exception as e:
                logger.error(f"Initial sync failed for device {device_id}: {e}")
                return {"error": str(e)}

    return run_async(_initial_sync())
