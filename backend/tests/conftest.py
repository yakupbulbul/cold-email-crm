"""
conftest.py — pytest fixtures for the Cold Email CRM backend test suite.

Uses a separate test database with per-session transaction rollbacks so
tests remain isolated and do not mutate production/staging data.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Force test DB before any app imports
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://user:password@localhost:5432/cold_email_test",
)
os.environ.setdefault("POSTGRES_URL", TEST_DB_URL)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from app.main import app
from app.models.base import Base
from app.core.database import get_db

engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per session, drop on teardown."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Per-test DB session that rolls back changes after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden DB dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    """Return Authorization headers for a seeded admin user."""
    from app.models.user import User
    from app.core.security import get_password_hash
    
    db = next(client.app.dependency_overrides[get_db]())

    # Create admin if not exists
    user = db.query(User).filter(User.email == "test@admin.com").first()
    if not user:
        user = User(
            email="test@admin.com",
            hashed_password=get_password_hash("test1234"),
            is_active=True,
        )
        db.add(user)
        db.commit()

    resp = client.post("/api/v1/auth/login", json={"email": "test@admin.com", "password": "test1234"})
    if resp.status_code != 200:
        return {}  # Auth may not be mandatory for all endpoints
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
