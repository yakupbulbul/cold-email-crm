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
    "postgresql://user:password@localhost:5433/cold_email_test",
)
os.environ.setdefault("POSTGRES_URL", TEST_DB_URL)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/1")
os.environ.setdefault("APP_ENV", "test")

from app.main import app
from app.models.base import Base
from app.core.database import get_db
from app.api.v1.routes import auth as auth_routes
from tests.factories import (
    campaign_payload,
    create_campaign,
    create_domain,
    create_mailbox,
    create_suppression_entry,
    create_user,
)
from tests.utils.mailcow import mocked_mailcow_response

engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def create_tables():
    """Create all tables once per session, drop on teardown."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(create_tables) -> Generator[Session, None, None]:
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
    previous_app_limiter = getattr(app.state.limiter, "enabled", True)
    previous_auth_limiter = getattr(auth_routes.limiter, "enabled", True)
    app.state.limiter.enabled = False
    auth_routes.limiter.enabled = False
    with TestClient(app) as c:
        yield c
    app.state.limiter.enabled = previous_app_limiter
    auth_routes.limiter.enabled = previous_auth_limiter
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    """Return Authorization headers for a seeded admin user."""
    return _issue_token(client, "test-admin@example.com", "test1234", is_admin=True)


@pytest.fixture()
def user_headers(client: TestClient) -> dict:
    """Return Authorization headers for a seeded non-admin user."""
    return _issue_token(client, "test-user@example.com", "test1234", is_admin=False)


@pytest.fixture()
def admin_user(db: Session):
    return create_user(
        db,
        email="test-admin@example.com",
        password="test1234",
        is_admin=True,
        full_name="Test Admin",
    )


@pytest.fixture()
def regular_user(db: Session):
    return create_user(
        db,
        email="test-user@example.com",
        password="test1234",
        is_admin=False,
        full_name="Test User",
    )


@pytest.fixture()
def domain_factory(db: Session):
    def factory(**kwargs):
        return create_domain(db, **kwargs)

    return factory


@pytest.fixture()
def mailbox_factory(db: Session):
    def factory(**kwargs):
        return create_mailbox(db, **kwargs)

    return factory


@pytest.fixture()
def campaign_factory(db: Session):
    def factory(**kwargs):
        return create_campaign(db, **kwargs)

    return factory


@pytest.fixture()
def campaign_payload_factory():
    return campaign_payload


@pytest.fixture()
def suppression_factory(db: Session):
    def factory(**kwargs):
        return create_suppression_entry(db, **kwargs)

    return factory


@pytest.fixture()
def mock_mailcow_request(monkeypatch):
    calls: list[tuple[str, str]] = []

    def factory(*, status_code: int = 200, payload: dict | None = None):
        response = mocked_mailcow_response(status_code=status_code, payload=payload)

        def _request(self, method: str, path: str):
            calls.append((method, path))
            return response

        monkeypatch.setattr("app.integrations.mailcow.client.MailcowClient._request", _request)
        return calls

    return factory


def _issue_token(client: TestClient, email: str, password: str, *, is_admin: bool) -> dict:
    from app.models.user import User
    from app.core.security import get_password_hash
    
    db = next(client.app.dependency_overrides[get_db]())

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        return {}
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
