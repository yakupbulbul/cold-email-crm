from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
import redis
from app.core.redis import get_redis_client

router = APIRouter()

@router.get("/")
def health_check():
    """Basic health check"""
    return {"status": "ok", "service": "AI Cold Email CRM API"}

@router.get("/db")
def health_check_db(db: Session = Depends(get_db)):
    """Database connectivity health check"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database down: {str(e)}")

@router.get("/redis")
def health_check_redis(redis_client: redis.Redis = Depends(get_redis_client)):
    """Redis cache connectivity health check"""
    try:
        redis_client.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis down: {str(e)}")
