"""Celery tasks for background sensor synchronization"""

from datetime import datetime, timedelta

from celery import shared_task

from myome.core.logging import logger
from myome.sensors.ingestion import IngestionService
from myome.sensors.adapters.oura import OuraDevice


@shared_task(name="sync_user_devices")
def sync_user_devices(
    user_id: str,
    hours_back: int = 24,
) -> dict:
    """
    Sync all devices for a user
    
    Called periodically by Celery beat scheduler
    """
    import asyncio
    
    async def _sync():
        # TODO: Load user's device configurations from database
        # For now, this is a placeholder
        
        service = IngestionService(user_id)
        
        # Calculate time range
        end = datetime.utcnow()
        start = end - timedelta(hours=hours_back)
        
        # Sync all devices
        results = await service.sync_all_devices(start, end)
        
        return results
    
    return asyncio.run(_sync())


@shared_task(name="sync_oura_device")
def sync_oura_device(
    user_id: str,
    access_token: str,
    hours_back: int = 24,
) -> dict:
    """Sync Oura Ring data for a user"""
    import asyncio
    
    async def _sync():
        service = IngestionService(user_id)
        
        # Create Oura device
        oura = OuraDevice(access_token)
        service.add_device("oura", oura)
        
        # Sync
        end = datetime.utcnow()
        start = end - timedelta(hours=hours_back)
        
        results = await service.sync_device("oura", start, end)
        
        logger.info(f"Oura sync for user {user_id}: {results}")
        return results
    
    return asyncio.run(_sync())
