from fastapi import APIRouter
from app.api.v1.routes import health, sending, warmup, campaigns, ai, auth, leads

api_router = APIRouter()

# Core system routes
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(sending.router, prefix="", tags=["sending"])
api_router.include_router(warmup.router, prefix="/warmup", tags=["warmup"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])

# Future grouped endpoints
# api_router.include_router(domains.router, prefix="/domains", tags=["domains"])
# api_router.include_router(mailboxes.router, prefix="/mailboxes", tags=["mailboxes"])
# ...
