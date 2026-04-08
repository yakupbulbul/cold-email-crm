from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.suppression import SuppressionList
from pydantic import BaseModel, UUID4

router = APIRouter()

class SuppressionCreate(BaseModel):
    email: str
    reason: str
    notes: str = None
    source: str = "manual"

class SuppressionCheck(BaseModel):
    emails: List[str]

@router.get("/")
@router.get("")  # Handle both /suppression and /suppression/ without redirect
def get_suppressions(db: Session = Depends(get_db)):
    return db.query(SuppressionList).all()

@router.post("/")
@router.post("")  # Handle both /suppression and /suppression/ without redirect
def add_suppression(req: SuppressionCreate, db: Session = Depends(get_db)):
    email_clean = req.email.strip().lower()
    existing = db.query(SuppressionList).filter(SuppressionList.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already suppressed")
    
    suppression = SuppressionList(
        email=email_clean,
        reason=req.reason,
        notes=req.notes,
        source=req.source
    )
    db.add(suppression)
    
    # Cascade to contacts marking them formally suppressed
    from app.models.campaign import Contact
    contact = db.query(Contact).filter(Contact.email == email_clean).first()
    if contact:
        contact.is_suppressed = True
        contact.unsubscribe_status = "suppressed"

    db.commit()
    return {"status": "success", "id": suppression.id}

@router.delete("/{id}")
def delete_suppression(id: str, db: Session = Depends(get_db)):
    suppression = db.query(SuppressionList).filter(SuppressionList.id == id).first()
    if not suppression:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Remove strict suppression flags if removed from core block
    from app.models.campaign import Contact
    contact = db.query(Contact).filter(Contact.email == suppression.email).first()
    if contact:
        contact.is_suppressed = False
        if contact.unsubscribe_status == "suppressed":
            contact.unsubscribe_status = "subscribed"

    db.delete(suppression)
    db.commit()
    return {"status": "deleted"}

@router.post("/check")
def check_suppression(req: SuppressionCheck, db: Session = Depends(get_db)):
    emails = [e.strip().lower() for e in req.emails]
    suppressed = db.query(SuppressionList.email).filter(SuppressionList.email.in_(emails)).all()
    return {"suppressed_emails": [s[0] for s in suppressed]}
