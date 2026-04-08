from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.core.database import get_db
from app.models.core import Domain
from app.services.domain_verification_service import DomainVerificationService

router = APIRouter()

class DomainCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_domain_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Domain name is required")
        if "." not in normalized or normalized.startswith(".") or normalized.endswith("."):
            raise ValueError("Enter a valid domain such as example.com")
        return normalized


def serialize_domain(domain: Domain) -> dict:
    return {
        "id": str(domain.id),
        "name": domain.name,
        "status": domain.status,
        "mailcow_status": domain.mailcow_status,
        "mailcow_detail": domain.mailcow_detail,
        "spf_status": domain.spf_status,
        "dkim_status": domain.dkim_status,
        "dmarc_status": domain.dmarc_status,
        "mx_status": domain.mx_status,
        "dns_results": domain.dns_results or {},
        "missing_requirements": domain.missing_requirements or [],
        "verification_summary": domain.verification_summary or {},
        "verification_error": domain.verification_error,
        "last_checked_at": domain.last_checked_at.isoformat() if domain.last_checked_at else None,
        "mailcow_last_checked_at": domain.mailcow_last_checked_at.isoformat() if domain.mailcow_last_checked_at else None,
        "dns_last_checked_at": domain.dns_last_checked_at.isoformat() if domain.dns_last_checked_at else None,
        "created_at": domain.created_at.isoformat() if domain.created_at else None,
        "updated_at": domain.updated_at.isoformat() if domain.updated_at else None,
    }


def get_domain_or_404(domain_id: str, db: Session) -> Domain:
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain

@router.get("/")
@router.get("")  # Handle both /domains and /domains/ without redirect
def list_domains(db: Session = Depends(get_db)):
    domains = db.query(Domain).order_by(Domain.created_at.desc()).all()
    return [serialize_domain(domain) for domain in domains]

@router.post("/")
@router.post("")  # Handle both /domains and /domains/ without redirect
def create_domain(req: DomainCreate, db: Session = Depends(get_db)):
    existing = db.query(Domain).filter(Domain.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    domain = Domain(
        name=req.name,
        status="pending",
        mailcow_status="pending",
        spf_status="pending",
        dkim_status="pending",
        dmarc_status="pending",
        mx_status="pending",
        last_checked_at=None,
        mailcow_last_checked_at=None,
        dns_last_checked_at=None,
        verification_summary={"readiness": {"status": "pending", "missing_requirements": []}},
        dns_results={},
        missing_requirements=[],
        verification_error=None,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    verified = DomainVerificationService(db).verify_domain(domain)
    return serialize_domain(verified)

@router.get("/{domain_id}")
def get_domain(domain_id: str, db: Session = Depends(get_db)):
    domain = get_domain_or_404(domain_id, db)
    return serialize_domain(domain)


@router.delete("/{domain_id}")
def delete_domain(domain_id: str, db: Session = Depends(get_db)):
    domain = get_domain_or_404(domain_id, db)
    db.delete(domain)
    db.commit()
    return {"status": "success", "id": domain_id}


@router.post("/{domain_id}/verify")
def verify_domain(domain_id: str, db: Session = Depends(get_db)):
    domain = get_domain_or_404(domain_id, db)
    verified = DomainVerificationService(db).verify_domain(domain)
    return serialize_domain(verified)


@router.post("/{domain_id}/refresh")
def refresh_domain(domain_id: str, db: Session = Depends(get_db)):
    domain = get_domain_or_404(domain_id, db)
    verified = DomainVerificationService(db).verify_domain(domain)
    return serialize_domain(verified)


@router.get("/{domain_id}/status")
def get_domain_status(domain_id: str, db: Session = Depends(get_db)):
    domain = get_domain_or_404(domain_id, db)
    return {
        "id": str(domain.id),
        "name": domain.name,
        "status": domain.status,
        "mailcow_status": domain.mailcow_status,
        "dns": {
            "mx": domain.mx_status,
            "spf": domain.spf_status,
            "dkim": domain.dkim_status,
            "dmarc": domain.dmarc_status,
        },
        "missing_requirements": domain.missing_requirements or [],
        "last_checked_at": domain.last_checked_at.isoformat() if domain.last_checked_at else None,
        "updated_at": domain.updated_at.isoformat() if domain.updated_at else datetime.utcnow().isoformat(),
    }
