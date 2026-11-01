"""
Celery Application for Worker Service.
Distributed task queue for scraping and retraining jobs.
"""
from celery import Celery
import os

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery = Celery(
    "bvc_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.worker_service.tasks"]
)

# Configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Optional: Periodic tasks (Celery Beat)
from celery.schedules import crontab

celery.conf.beat_schedule = {
    "morning-bvc-scrape": {
        "task": "services.worker_service.tasks.scrape_bvc_bulletins",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
    },
    "afternoon-ammc-scrape": {
        "task": "services.worker_service.tasks.scrape_ammc_catalysts",
        "schedule": crontab(hour=14, minute=30),  # 2:30 PM daily
    },
    "weekly-model-retrain": {
        "task": "services.worker_service.tasks.retrain_model",
        "schedule": crontab(day_of_week="sunday", hour=2, minute=0),  # Sunday 2 AM
    },
    "daily-cleanup": {
        "task": "services.worker_service.tasks.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0),  # 3:00 AM daily
    },
}

if __name__ == "__main__":
    celery.start()
