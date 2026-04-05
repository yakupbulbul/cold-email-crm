from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import User as UserSchema
from app.core.auth import create_access_token
from app.core.security import verify_password
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
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

