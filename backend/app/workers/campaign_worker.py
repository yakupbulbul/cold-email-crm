from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.campaign_service import CampaignService
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_campaign_cycle():
    db = SessionLocal()
    try:
        logger.info("Starting Campaign Dispatch Engine cycle")
        service = CampaignService(db)
        service.process_active_campaigns()
    except Exception as e:
        logger.error(f"Campaign Worker Error: {e}")
    finally:
        db.close()
