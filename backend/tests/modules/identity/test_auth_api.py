import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.domain.entities import User
from app.modules.identity.domain.enums import UserStatus
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from app.modules.identity.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.identity.infrastructure.security.argon2_password_hasher import Argon2idPasswordHasher


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _seed_active_user(db_session: Session, email: str, password: str) -> User:
    hasher = Argon2idPasswordHasher()
    user_repo = SqlAlchemyUserRepository(db_session)
    return user_repo.create(
        User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hasher.hash(password),
            status=UserStatus.ACTIVE,
            is_super_admin=False,
            created_at=_now(),
            updated_at=_now(),
        )
    )


def test_auth_login_success(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"]
    assert body["refresh_token"]


def test_auth_login_invalid_credentials(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_auth_refresh_success(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["access_token"]
    assert body["refresh_token"] != refresh_token


def test_auth_logout_returns_204(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
