from pydantic import BaseModel, UUID4
from typing import List, Dict, Any, Optional
from datetime import datetime

class ImportMappingRules(BaseModel):
    # Dict mapping system fields (e.g. 'email', 'first_name') to CSV column indices
    field_mappings: Dict[str, str]
    campaign_id: Optional[UUID4] = None

class ImportJobResponse(BaseModel):
    id: UUID4
    file_name: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    imported_rows: int
    created_at: datetime
