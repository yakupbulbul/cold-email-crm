from datetime import datetime
from typing import Any

from pydantic import BaseModel, UUID4


class QualityCheckResultResponse(BaseModel):
    id: UUID4 | None = None
    run_id: UUID4 | None = None
    status: str
    category: str
    name: str
    message: str
    severity: str
    entity_type: str | None = None
    entity_id: UUID4 | None = None
    href: str | None = None
    metadata: dict[str, Any] | None = None
    checked_at: datetime


class QualityCheckRunResponse(BaseModel):
    id: UUID4
    run_type: str
    status: str
    summary: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    results: list[QualityCheckResultResponse] = []


class QualityCenterSummary(BaseModel):
    overall_status: str
    generated_at: datetime
    last_smoke_run: QualityCheckRunResponse | None = None
    last_release_run: QualityCheckRunResponse | None = None
    failing_checks: list[QualityCheckResultResponse]
    stale_checks: list[QualityCheckResultResponse]
    recommended_next_fixes: list[str]
    recent_runs: list[QualityCheckRunResponse]
    runtime_checks: list[QualityCheckResultResponse]
    integrity_checks: list[QualityCheckResultResponse]
    stats: dict[str, int]

