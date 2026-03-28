from fastapi import APIRouter
from app.api.v1.routes import health, sending

api_router = APIRouter()

# Core system routes
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sending.router, prefix="", tags=["sending"])

# Future grouped endpoints
# api_router.include_router(domains.router, prefix="/domains", tags=["domains"])
# api_router.include_router(mailboxes.router, prefix="/mailboxes", tags=["mailboxes"])
# ...
