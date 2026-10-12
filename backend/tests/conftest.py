import os

# Must run before `app` is imported: settings are read once at import time, and real
# environment variables take precedence over backend/.env. This keeps the suite offline
# (no AI keys -> MockLLMProvider) and off the developer's dev.db.
os.environ.update(
    {
        "DATABASE_URL": "sqlite://",
        "OPENAI_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "AI_MODEL_PROFILES": "",
        "SMTP_HOST": "",
        "SECRET_KEY": "test-secret-key-not-for-production",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  - registers every table on Base.metadata
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_session_factory():
    # StaticPool: one shared connection, so the in-memory database survives across the
    # request threads TestClient uses.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def client(db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "recruiter@example.com", "password": "s3cret-pass", "full_name": "Test Recruiter"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
