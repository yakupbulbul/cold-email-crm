import csv
import io
import re
from sqlalchemy.orm import Session
from app.models.import_job import LeadImportJob, LeadImportRow
from app.models.campaign import Contact
from app.schemas.import_job import ImportMappingRules

class LeadValidationService:
    @staticmethod
    def validate_row(mapped_data: dict, db: Session) -> tuple[str, str]:
        email = mapped_data.get("email", "").strip().lower()
        if not email:
            return "invalid", "Missing email address"
            
        # Basic regex check
        email_regex = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
        if not email_regex.match(email):
            return "invalid", "Malformed email address"
            
        # Check if already exists in DB
        exists = db.query(Contact).filter(Contact.email == email).first()
        if exists:
            return "duplicate_in_database", "Email already exists in contacts"
            
        return "valid", ""

class CSVParserService:
    def __init__(self, db: Session):
        self.db = db

    def create_import_job(self, file_content: bytes, file_name: str) -> LeadImportJob:
        content_str = file_content.decode('utf-8', errors='replace')
        f = io.StringIO(content_str)
        reader = csv.reader(f)
        
        headers = next(reader, [])
        
        job = LeadImportJob(
            file_name=file_name,
            status="parsed",
            total_rows=0
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        rows_to_insert = []
        for i, row in enumerate(reader, start=1):
            raw_data = {headers[j] if j < len(headers) else f"col_{j}": val for j, val in enumerate(row)}
            rows_to_insert.append(
                LeadImportRow(
                    job_id=job.id,
                    row_index=i,
                    raw_data=raw_data
                )
            )
        
        job.total_rows = len(rows_to_insert)
        self.db.bulk_save_objects(rows_to_insert)
        self.db.commit()
        
        return job

class LeadImportJobService:
    def __init__(self, db: Session):
        self.db = db
        
    def validate_and_map_job(self, job_id: str, mappings: ImportMappingRules):
        job = self.db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
        if not job:
            return
            
        rows = self.db.query(LeadImportRow).filter(LeadImportRow.job_id == job_id).all()
        
        email_hash_set = set()
        
        valid_count = 0
        invalid_count = 0
        duplicate_count = 0
        
        for row in rows:
            mapped_data = {}
            for system_field, csv_header in mappings.field_mappings.items():
                mapped_data[system_field] = row.raw_data.get(csv_header, "")
                
            email = mapped_data.get("email", "").strip().lower()
            
            row.mapped_email = email
            row.mapped_first_name = mapped_data.get("first_name", "")
            row.mapped_last_name = mapped_data.get("last_name", "")
            row.mapped_company = mapped_data.get("company", "")
            
            # File duplicate collision prevention
            if email in email_hash_set:
                row.validation_status = "duplicate_in_file"
                row.validation_reason = "Duplicate email in the uploaded file"
                duplicate_count += 1
                continue
            
            if email:
                email_hash_set.add(email)
                
            # Full validation step
            status, reason = LeadValidationService.validate_row(mapped_data, self.db)
            row.validation_status = status
            row.validation_reason = reason
            
            if status == "valid":
                valid_count += 1
            elif status == "invalid":
                invalid_count += 1
            elif status == "duplicate_in_database":
                duplicate_count += 1
                
        job.valid_rows = valid_count
        job.invalid_rows = invalid_count
        job.duplicate_rows = duplicate_count
        job.status = "validated"
        job.campaign_id = mappings.campaign_id
        
        self.db.commit()

    def confirm_and_import(self, job_id: str):
        job = self.db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
        if not job or job.status != "validated":
            return
            
        valid_rows = self.db.query(LeadImportRow).filter(
            LeadImportRow.job_id == job_id, 
            LeadImportRow.validation_status == "valid"
        ).all()
        
        imported_count = 0
        for row in valid_rows:
            contact = Contact(
                email=row.mapped_email,
                first_name=row.mapped_first_name,
                last_name=row.mapped_last_name,
                company=row.mapped_company,
                source="CSV Import",
                notes=f"Imported from job {job_id}"
            )
            self.db.add(contact)
            self.db.flush() # get contact.id
            
            row.validation_status = "imported"
            row.imported_contact_id = contact.id
            imported_count += 1
            
            if job.campaign_id:
                from app.models.campaign import CampaignLead
                lead = CampaignLead(
                    campaign_id=job.campaign_id,
                    contact_id=contact.id
                )
                self.db.add(lead)
                
        job.imported_rows = imported_count
        job.status = "completed"
        self.db.commit()
