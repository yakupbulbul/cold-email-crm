from pydantic import BaseModel


class WarmupMailboxToggleRequest(BaseModel):
    warmup_enabled: bool


class WarmupGlobalActionResponse(BaseModel):
    status: str
    detail: str
    job_queued: bool | None = None
    job_id: str | None = None

