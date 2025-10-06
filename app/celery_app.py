"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "todolist",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.notification_tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Configure Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "send-daily-reminders": {
        "task": "app.tasks.notification_tasks.send_daily_reminders_task",
        "schedule": crontab(hour=12, minute=30),  # Run at 12:30 PM UTC (TESTING)
        # "schedule": crontab(minute="*/5"),  # Run every 5 minutes

        "options": {"expires": 3600},  # Task expires after 1 hour
    },
}

# Optional: Configure task routes
celery_app.conf.task_routes = {
    "app.tasks.notification_tasks.*": {"queue": "notifications"},
}
