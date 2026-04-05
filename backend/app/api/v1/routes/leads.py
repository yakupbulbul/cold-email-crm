from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.verification_service import EmailVerificationService
from app.schemas.import_job import ImportMappingRules
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import io
import csv

from app.models.campaign import Contact

router = APIRouter()

@router.get("/")
def list_leads(db: Session = Depends(get_db)):
    return db.query(Contact).all()

@router.post("/import/csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be CSV.")
    
    contents = await file.read()
    parser = CSVParserService(db)
    job = parser.create_import_job(contents, file.filename)
    
    return {"job_id": job.id, "status": job.status, "total_rows_parsed": job.total_rows}

@router.post("/import/{job_id}/map")
def map_and_validate_import(job_id: str, mappings: ImportMappingRules, db: Session = Depends(get_db)):
    importer = LeadImportJobService(db)
    importer.validate_and_map_job(job_id, mappings)
    
    # Fetch updated job
    from app.models.import_job import LeadImportJob
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": job.id,
        "status": job.status,
        "valid_rows": job.valid_rows,
        "invalid_rows": job.invalid_rows,
        "duplicate_rows": job.duplicate_rows
    }

@router.post("/import/{job_id}/confirm")
def confirm_import(job_id: str, db: Session = Depends(get_db)):
    importer = LeadImportJobService(db)
    importer.confirm_and_import(job_id)
    
    from app.models.import_job import LeadImportJob
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    return {"job_id": job.id, "status": job.status, "imported_rows": job.imported_rows}

@router.get("/import/{job_id}")
def get_import_job(job_id: str, db: Session = Depends(get_db)):
    from app.models.import_job import LeadImportJob, LeadImportRow
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    rows = db.query(LeadImportRow).filter(LeadImportRow.job_id == job_id).limit(100).all()
    
    return {
        "job": {
            "id": job.id,
            "file_name": job.file_name,
            "status": job.status,
            "total": job.total_rows,
            "valid": job.valid_rows,
            "invalid": job.invalid_rows
        },
        "preview_rows": rows
    }

class VerifyRequest(BaseModel):
    email: str

@router.post("/verify")
def verify_email(req: VerifyRequest, db: Session = Depends(get_db)):
    service = EmailVerificationService(db)
    log = service.verify_email(req.email)
    
    return {
        "status": log.final_status,
        "score": log.verification_score,
        "syntax_valid": log.syntax_valid,
        "mx_valid": log.mx_valid,
    }

def generate_csv_response(contacts, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "First Name", "Last Name", "Company", "Verification Score", "Suppressed"])
    for c in contacts:
        writer.writerow([c.email, c.first_name, c.last_name, c.company, c.verification_score, c.is_suppressed])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/export")
def export_all_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = db.query(Contact).all()
    return generate_csv_response(contacts, "all_contacts.csv")

@router.get("/export/invalid")
def export_invalid_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = db.query(Contact).filter(Contact.verification_score < 80).all()
    return generate_csv_response(contacts, "invalid_contacts.csv")

@router.get("/export/suppressed")
def export_suppressed_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = db.query(Contact).filter(Contact.is_suppressed == True).all()
    return generate_csv_response(contacts, "suppressed_contacts.csv")
