import os
from importlib import import_module

from celery import Celery

from app.core.config import settings

TASK_MODULES = [
    "app.workers.heartbeat_worker",
    "app.workers.imap_sync_worker",
    "app.workers.warmup_worker",
    "app.workers.campaign_worker",
]

os.environ.setdefault('CELERY_BROKER_URL', settings.REDIS_URL)

celery_app = Celery(
    "cold_email_crm",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=TASK_MODULES,
)

celery_app.conf.imports = TASK_MODULES

for module in TASK_MODULES:
    import_module(module)

beat_schedule = {
    "record-worker-heartbeat-every-30-seconds": {
        "task": "app.workers.heartbeat_worker.record_pipeline_heartbeat",
        "schedule": 30.0,
    },
    "run-warmup-every-15-minutes": {
        "task": "app.workers.warmup_worker.run_warmup_cycle",
        "schedule": 900.0,  # Every 15 minutes adds natural randomization
    },
    "run-campaigns-every-5-minutes": {
        "task": "app.workers.campaign_worker.run_campaign_cycle",
        "schedule": 300.0,
    },
}

if settings.BACKGROUND_IMAP_SYNC_ENABLED:
    beat_schedule["sync-inboxes-every-minute"] = {
        "task": "app.workers.imap_sync_worker.sync_all_inboxes",
        "schedule": 60.0,
    }

celery_app.conf.beat_schedule = beat_schedule
