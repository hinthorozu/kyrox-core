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
from app.modules.identity.domain.authentication.value_objects.security.access_token import AccessToken
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories import SqlAlchemyUserRepository
from app.modules.identity.infrastructure.authentication.security import (
    Argon2idPasswordHasher,
    JwtTokenService,
)
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


def test_authentication_end_to_end_flow(client: TestClient, db_session: Session) -> None:
    _seed_active_user(db_session, "e2e@example.com", "password123")
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]
    assert access_token
    assert refresh_token

    token_service = JwtTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    claims = token_service.decode_access_token(AccessToken.create(access_token))
    assert claims.email.value == "e2e@example.com"

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    refresh_body = refresh_response.json()
    new_access_token = refresh_body["access_token"]
    new_refresh_token = refresh_body["refresh_token"]
    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    old_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert old_refresh_response.status_code == 401

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh_token},
    )
    assert logout_response.status_code == 204

    post_logout_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh_token},
    )
    assert post_logout_refresh_response.status_code == 401
