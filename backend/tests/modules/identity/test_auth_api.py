import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.domain.authentication.entities.user import User as AuthUser
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import PasswordHash
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


def _seed_active_user(
    db_session: Session,
    email: str,
    password: str,
    *,
    must_change_password: bool = False,
) -> AuthUser:
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
            must_change_password=must_change_password,
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
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    assert body["must_change_password"] is False
    assert body["access_token"]
    assert body["refresh_token"]


def test_auth_login_exposes_forced_password_change(client: TestClient, db_session: Session) -> None:
    _seed_active_user(
        db_session,
        "forced@example.com",
        "temporary123",
        must_change_password=True,
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "forced@example.com", "password": "temporary123"},
    )

    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_change_password_clears_forced_state(client: TestClient, db_session: Session) -> None:
    user = _seed_active_user(
        db_session,
        "forced@example.com",
        "temporary123",
        must_change_password=True,
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "forced@example.com", "password": "temporary123"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "temporary123", "new_password": "permanent123"},
    )

    assert response.status_code == 204
    db_session.expire_all()
    stored = db_session.get(identity_models.UserModel, user.id.value)
    assert stored is not None
    assert stored.must_change_password is False
    assert Argon2idPasswordHasher().verify(
        "permanent123",
        PasswordHash(stored.password_hash),
    )


def test_change_password_rejects_same_password(client: TestClient, db_session: Session) -> None:
    _seed_active_user(
        db_session,
        "forced@example.com",
        "temporary123",
        must_change_password=True,
    )
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "forced@example.com", "password": "temporary123"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "temporary123", "new_password": "temporary123"},
    )

    assert response.status_code == 400


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
