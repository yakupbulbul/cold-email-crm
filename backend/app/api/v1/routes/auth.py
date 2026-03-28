from fastapi import APIRouter, HTTPException, Request
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.auth import create_access_token
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_access_token(request: Request, req: LoginRequest):
    if req.email == "dev@example.com" and req.password == "admin":
        access_token = create_access_token(subject=req.email)
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect email or password")
