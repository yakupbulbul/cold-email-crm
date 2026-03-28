import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "cold_email_crm",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.warmup_worker", "app.workers.sync_worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Setup beat schedule
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'run-warmup-cycle-every-15-minutes': {
        'task': 'app.workers.warmup_worker.process_warmups',
        'schedule': crontab(minute='*/15'),
    },
    'sync-inboxes-every-5-minutes': {
        'task': 'app.workers.sync_worker.sync_all_mailboxes',
        'schedule': crontab(minute='*/5'),
    },
}
