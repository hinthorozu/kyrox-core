import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import get_db
from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.dependencies import get_authorization_service
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.application.authorization import AuthorizationService
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessTokenClaims,
)
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.entities import Organization, User
from app.modules.identity.infrastructure.authentication.security.jwt_token_service import (
    JwtTokenService,
)
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from authorization_test_helpers import build_authorization_service, seed_user_role_with_permission


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


def _seed(db_session: Session) -> tuple[User, Organization, str]:
    seed = seed_user_role_with_permission(db_session)
    token_service = JwtTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    now = datetime.now(UTC)
    access_token = token_service.create_access_token(
        AccessTokenClaims(
            sub=UserId(seed.user.id),
            email=Email(value=seed.user.email),
            sid=SessionId(uuid.uuid4()),
            exp=now + timedelta(minutes=15),
            iat=now,
            jti=uuid.uuid4(),
        )
    )
    return seed.user, seed.org, access_token.value


@pytest.fixture
def guard_client(db_session: Session) -> Generator[TestClient, None, None]:
    router = APIRouter()

    @router.get("/protected")
    def protected_route(
        context: AuthorizationContext = Depends(require_permission("core.user.read")),
    ) -> dict[str, str]:
        return {
            "user_id": str(context.user_id),
            "organization_id": str(context.organization_id),
        }

    @router.get("/denied")
    def denied_route(
        context: AuthorizationContext = Depends(require_permission("core.user.create")),
    ) -> dict[str, str]:
        return {"user_id": str(context.user_id)}

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    def override_auth_service() -> AuthorizationService:
        return build_authorization_service(db_session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authorization_service] = override_auth_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_guard_rejects_missing_bearer_token(guard_client: TestClient, db_session: Session) -> None:
    _user, org, _token = _seed(db_session)

    response = guard_client.get(
        "/protected",
        headers={"X-Organization-Id": str(org.id)},
    )

    assert response.status_code == 401


def test_guard_rejects_invalid_bearer_token(guard_client: TestClient, db_session: Session) -> None:
    _user, org, _token = _seed(db_session)

    response = guard_client.get(
        "/protected",
        headers={
            "Authorization": "Bearer invalid-token",
            "X-Organization-Id": str(org.id),
        },
    )

    assert response.status_code == 401


def test_guard_rejects_missing_organization_header(
    guard_client: TestClient,
    db_session: Session,
) -> None:
    _user, _org, token = _seed(db_session)

    response = guard_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_guard_rejects_missing_permission(
    guard_client: TestClient,
    db_session: Session,
) -> None:
    _user, org, token = _seed(db_session)

    response = guard_client.get(
        "/denied",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id),
        },
    )

    assert response.status_code == 403


def test_guard_allows_authorized_request(
    guard_client: TestClient,
    db_session: Session,
) -> None:
    user, org, token = _seed(db_session)

    response = guard_client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)
    assert response.json()["organization_id"] == str(org.id)
