"""Database session management for MCP server context."""

from contextlib import contextmanager

from app.core.database import SessionLocal


@contextmanager
def get_db_session():
    """Provide a transactional database session for MCP tool handlers."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
