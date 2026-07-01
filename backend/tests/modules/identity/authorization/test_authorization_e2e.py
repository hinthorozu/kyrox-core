from collections.abc import Generator
import sys
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from authorization_test_helpers import seed_user_role_with_permission


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
    router = APIRouter()

    @router.get("/authorization/protected")
    def protected_route(
        context: AuthorizationContext = Depends(require_permission("core.user.read")),
    ) -> dict[str, str]:
        return {
            "user_id": str(context.user_id),
            "organization_id": str(context.organization_id),
        }

    @router.get("/authorization/denied")
    def denied_route(
        context: AuthorizationContext = Depends(require_permission("core.user.create")),
    ) -> dict[str, str]:
        return {"user_id": str(context.user_id)}

    app = create_app()
    app.include_router(router, prefix="/api/v1")

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_authorization_end_to_end_flow(client: TestClient, db_session: Session) -> None:
    seed = seed_user_role_with_permission(db_session)
    user = seed.user_repo.get_by_id(seed.user.id)
    assert user is not None
    user.password_hash = Argon2idPasswordHasher().hash("password123").value
    seed.user_repo.update(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": seed.user.email, "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    denied_response = client.get(
        "/api/v1/authorization/denied",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Organization-Id": str(seed.org.id),
        },
    )
    assert denied_response.status_code == 403

    protected_response = client.get(
        "/api/v1/authorization/protected",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Organization-Id": str(seed.org.id),
        },
    )
    assert protected_response.status_code == 200
    assert protected_response.json()["user_id"] == str(seed.user.id)
    assert protected_response.json()["organization_id"] == str(seed.org.id)
