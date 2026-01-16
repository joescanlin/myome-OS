"""Celery application configuration"""

from celery import Celery

from myome.core.config import settings

celery_app = Celery(
    "myome",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=["myome.sensors.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "sync-all-users-hourly": {
        "task": "sync_user_devices",
        "schedule": 3600,  # Every hour
        "args": [],
    },
}
