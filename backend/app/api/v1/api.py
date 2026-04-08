from fastapi import APIRouter, Depends
from app.api.v1.routes import health, sending, warmup, campaigns, ai, auth, leads, suppression, ops, ops_deliverability, domains, mailboxes, inbox, settings
from app.api.deps import get_current_active_user, get_current_active_admin

api_router = APIRouter()

# Core system routes
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Authenticated Core Routes
api_router.include_router(leads.router, prefix="/leads", tags=["leads"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(suppression.router, prefix="/suppression", tags=["suppression"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(warmup.router, prefix="/warmup", tags=["warmup"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(sending.router, prefix="", tags=["sending"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(domains.router, prefix="/domains", tags=["domains"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(mailboxes.router, prefix="/mailboxes", tags=["mailboxes"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"], dependencies=[Depends(get_current_active_user)])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_active_user)])

# Admin Protected Routes
api_router.include_router(ops.router, prefix="/ops", tags=["ops"], dependencies=[Depends(get_current_active_admin)])
api_router.include_router(ops_deliverability.router, prefix="/ops/deliverability", tags=["ops_deliverability"], dependencies=[Depends(get_current_active_admin)])
