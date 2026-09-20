import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.domain.authentication.entities.user import User as AuthUser
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories import SqlAlchemyUserRepository
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401


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


def _seed_active_user(db_session: Session, email: str, password: str) -> AuthUser:
    hasher = Argon2idPasswordHasher()
    clock = UtcClock()
    user_repo = SqlAlchemyUserRepository(db_session, clock)
    now = clock.now()
    return user_repo.add(
        AuthUser(
            id=UserId(uuid.uuid4()),
            email=Email.create(email),
            password_hash=hasher.hash(password),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
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
    assert body["expires_in"] == 15 * 24 * 60 * 60
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


def test_auth_login_replaces_existing_session(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "user@example.com", "password123")
    other = _seed_active_user(db_session, "other@example.com", "password123")
    db_session.commit()

    first = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other.email.value, "password": "password123"},
    )
    assert first.status_code == 200
    assert other_login.status_code == 200
    first_access = first.json()["access_token"]
    first_refresh = first.json()["refresh_token"]
    other_refresh = other_login.json()["refresh_token"]

    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )
    assert failed.status_code == 401
    still_valid = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert still_valid.status_code == 200
    first_refresh = still_valid.json()["refresh_token"]
    first_access = still_valid.json()["access_token"]

    second = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert second.status_code == 200
    second_refresh = second.json()["refresh_token"]
    second_access = second.json()["access_token"]

    stale_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert stale_refresh.status_code == 401

    stale_access = client.post(
        "/api/v1/auth/password/change",
        headers={"Authorization": f"Bearer {first_access}"},
        json={
            "current_password": "password123",
            "new_password": "replacement-password-123",
        },
    )
    assert stale_access.status_code == 401

    live_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert live_refresh.status_code == 200

    other_still_valid = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": other_refresh},
    )
    assert other_still_valid.status_code == 200
    assert second_access != first_access
