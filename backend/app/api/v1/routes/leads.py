from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.import_service import CSVParserService, LeadImportJobService
from app.schemas.import_job import ImportMappingRules

router = APIRouter()

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
