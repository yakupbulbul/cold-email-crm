from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import User as UserSchema
from app.core.auth import create_access_token
from app.core.config import settings
from app.core.security import verify_password
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.google_oauth_service import GoogleOAuthError, GoogleWorkspaceOAuthService
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_access_token(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user


def _frontend_mailboxes_url(*, mailbox_id: str | None = None, oauth_status: str | None = None, oauth_message: str | None = None) -> str:
    frontend_base = (settings.ALLOWED_ORIGINS[0] if settings.ALLOWED_ORIGINS else f"http://localhost:{settings.FRONTEND_PORT}").rstrip("/")
    query: dict[str, str] = {}
    if mailbox_id:
        query["mailbox_id"] = mailbox_id
    if oauth_status:
        query["oauth_status"] = oauth_status
    if oauth_message:
        query["oauth_message"] = oauth_message
    suffix = f"?{urlencode(query)}" if query else ""
    return f"{frontend_base}/mailboxes{suffix}"


@router.get("/google-workspace/callback")
def google_workspace_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    oauth_service = GoogleWorkspaceOAuthService(db)
    mailbox_id: str | None = None
    try:
        payload = oauth_service.decode_state(state)
        mailbox_id = payload.get("mailbox_id")
    except GoogleOAuthError:
        mailbox_id = None

    try:
        token = oauth_service.exchange_code(code=code, state=state)
    except GoogleOAuthError as exc:
        return RedirectResponse(
            url=_frontend_mailboxes_url(
                mailbox_id=mailbox_id,
                oauth_status=exc.category,
                oauth_message=exc.message,
            ),
            status_code=303,
        )

    connected_email = token.external_account_email or "the selected mailbox"
    return RedirectResponse(
        url=_frontend_mailboxes_url(
            mailbox_id=str(token.mailbox_id),
            oauth_status="connected",
            oauth_message=f"Google Workspace connected for {connected_email}.",
        ),
        status_code=303,
    )
