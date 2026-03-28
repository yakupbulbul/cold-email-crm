from celery import Celery
from app.core.config import settings
import os

os.environ.setdefault('CELERY_BROKER_URL', settings.REDIS_URL)

celery_app = Celery(
    "cold_email_crm",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.imap_sync_worker", "app.workers.warmup_worker"]
)

celery_app.conf.beat_schedule = {
    "sync-inboxes-every-minute": {
        "task": "app.workers.imap_sync_worker.sync_all_inboxes",
        "schedule": 60.0
    },
    "run-warmup-every-15-minutes": {
        "task": "app.workers.warmup_worker.run_warmup_cycle",
        "schedule": 900.0  # Every 15 minutes adds natural randomization
    }
}
