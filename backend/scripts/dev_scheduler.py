import logging
import time

from app.core.config import settings
from app.workers.campaign_worker import run_campaign_cycle
from app.workers.heartbeat_worker import record_pipeline_heartbeat
from app.workers.warmup_worker import run_warmup_cycle

logger = logging.getLogger("dev_scheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEARTBEAT_INTERVAL = 30
CAMPAIGN_INTERVAL = 300
WARMUP_INTERVAL = 900
IMAP_INTERVAL = 60


def main() -> None:
    logger.info("Starting dev scheduler loop")
    last_heartbeat = 0.0
    last_campaign = 0.0
    last_warmup = 0.0
    last_imap = 0.0

    sync_all_inboxes = None
    if settings.BACKGROUND_IMAP_SYNC_ENABLED:
        from app.workers.imap_sync_worker import sync_all_inboxes as sync_task

        sync_all_inboxes = sync_task

    while True:
        now = time.time()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            record_pipeline_heartbeat.delay()
            logger.info("Enqueued pipeline heartbeat")
            last_heartbeat = now

        if now - last_campaign >= CAMPAIGN_INTERVAL:
            run_campaign_cycle.delay()
            logger.info("Enqueued campaign cycle")
            last_campaign = now

        if now - last_warmup >= WARMUP_INTERVAL:
            run_warmup_cycle.delay()
            logger.info("Enqueued warmup cycle")
            last_warmup = now

        if sync_all_inboxes is not None and now - last_imap >= IMAP_INTERVAL:
            sync_all_inboxes.delay()
            logger.info("Enqueued inbox sync")
            last_imap = now

        time.sleep(1)


if __name__ == "__main__":
    main()
