from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.monitoring import WorkerHeartbeat
from app.workers.celery_app import celery_app


@celery_app.task(bind=True)
def record_pipeline_heartbeat(self):
    db = SessionLocal()
    try:
        worker_name = self.request.hostname or "unknown-worker"
        heartbeat = (
            db.query(WorkerHeartbeat)
            .filter(
                WorkerHeartbeat.worker_name == worker_name,
                WorkerHeartbeat.worker_type == "pipeline",
            )
            .first()
        )
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                worker_type="pipeline",
                status="healthy",
                last_seen_at=datetime.now(timezone.utc),
                metadata_blob={"source": "beat-scheduled-heartbeat"},
            )
            db.add(heartbeat)
        else:
            heartbeat.status = "healthy"
            heartbeat.last_seen_at = datetime.now(timezone.utc)
            heartbeat.metadata_blob = {"source": "beat-scheduled-heartbeat"}
        db.commit()
    finally:
        db.close()
