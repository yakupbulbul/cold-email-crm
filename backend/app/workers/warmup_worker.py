from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.warmup_service import WarmupService
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_warmup_cycle():
    db = SessionLocal()
    try:
        logger.info("Starting Warm-up Engine cycle")
        service = WarmupService(db)
        service.process_all_active_pairs()
    except Exception as e:
        logger.error(f"Warm-up Worker Error: {e}")
    finally:
        db.close()
