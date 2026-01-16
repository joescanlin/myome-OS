"""Celery application configuration"""

from celery import Celery
from celery.schedules import crontab

from myome.core.config import settings

celery_app = Celery(
    "myome",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=[
        "myome.sensors.tasks",
        "myome.integrations.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Sync all connected devices every 15 minutes
    "sync-all-devices": {
        "task": "myome.integrations.tasks.sync_all_devices",
        "schedule": 900,  # 15 minutes
    },
    # Run daily analytics at 3 AM UTC
    "daily-analytics": {
        "task": "myome.integrations.tasks.run_daily_analytics",
        "schedule": crontab(hour=3, minute=0),
    },
}
