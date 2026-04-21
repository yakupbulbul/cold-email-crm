from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.quality_center import QualityCenterSummary, QualityCheckResultResponse, QualityCheckRunResponse
from app.services.quality_center_service import QualityCenterService


router = APIRouter()


@router.get("/summary", response_model=QualityCenterSummary)
def quality_summary(db: Session = Depends(get_db)):
    return QualityCenterService(db).summary()


@router.get("/runs", response_model=list[QualityCheckRunResponse])
def quality_runs(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    return QualityCenterService(db).runs(limit=limit)


@router.get("/checks", response_model=list[QualityCheckResultResponse])
def quality_checks(db: Session = Depends(get_db)):
    return QualityCenterService(db).checks()


@router.post("/runs/smoke", response_model=QualityCheckRunResponse)
def run_smoke_quality_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return QualityCenterService(db).run_smoke(actor=current_user)


@router.post("/runs/release-readiness", response_model=QualityCheckRunResponse)
def run_release_readiness_quality_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return QualityCenterService(db).run_release_readiness(actor=current_user)

