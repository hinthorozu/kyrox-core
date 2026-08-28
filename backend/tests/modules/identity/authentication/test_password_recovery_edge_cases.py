import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.modules.identity.application.authentication.id_generator import Uuid4IdGenerator
from app.modules.identity.application.authentication.identity_action_tokens import (
    IssueIdentityActionToken,
)
from app.modules.identity.application.organization.policy import OrganizationNamingPolicy
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.infrastructure.authentication.repositories import (
    SqlAlchemyIdentityActionTokenRepository,
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.authentication.security import Argon2idPasswordHasher
from app.modules.identity.infrastructure.authentication.security.identity_action_token_service import (
    IdentityActionTokenService,
)
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)

_VALID_PASSWORD = "replacement password 123"


@dataclass
class MutableClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


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


def _seed_account(
    db_session: Session,
    *,
    status: UserStatus = UserStatus.ACTIVE,
    deleted_at: datetime | None = None,
) -> uuid.UUID:
    now = datetime.now(UTC)
    clock = MutableClock(now)
    ids = Uuid4IdGenerator()
    naming = OrganizationNamingPolicy()
    organization_id = OrganizationId(ids.generate_uuid())
    organization = SqlAlchemyOrganizationRepository(db_session, clock).add(
        Organization(
            id=organization_id,
            name=naming.normalize_name("Recovery Edge Organization"),
            slug=naming.normalize_slug(f"recovery-edge-{organization_id.value.hex[:12]}"),
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    user_id = UserId(ids.generate_uuid())
    SqlAlchemyUserRepository(db_session, clock).add(
        User(
            id=user_id,
            email=Email.create(f"edge-{user_id.value.hex[:8]}@example.com"),
            password_hash=Argon2idPasswordHasher().hash("existing password 123"),
            status=status,
            created_at=now,
            updated_at=now,
            deleted_at=deleted_at,
            organization_id=organization.id.value,
            is_super_admin=False,
        )
    )
    db_session.commit()
    return user_id.value


def _issue_reset_token(
    db_session: Session,
    *,
    user_id: uuid.UUID,
    clock: MutableClock,
    ttl: timedelta,
) -> tuple[str, object]:
    repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    issued = IssueIdentityActionToken(
        repository=repository,
        token_service=IdentityActionTokenService(
            settings.CORE_IDENTITY_ACTION_TOKEN_SECRET_KEY
        ),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    ).execute(
        UserId(user_id),
        IdentityActionTokenPurpose.PASSWORD_RESET,
        ttl,
        reconstructable=True,
    )
    db_session.commit()
    return issued.raw_token, issued.token_id


def _client_for(db_session: Session) -> tuple[TestClient, object]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), app


def test_password_reset_rejects_expired_token(db_session: Session) -> None:
    user_id = _seed_account(db_session)
    raw_token, token_id = _issue_reset_token(
        db_session,
        user_id=user_id,
        clock=MutableClock(datetime.now(UTC) - timedelta(minutes=2)),
        ttl=timedelta(minutes=1),
    )
    client, app = _client_for(db_session)
    try:
        with client:
            response = client.post(
                "/api/v1/auth/password/reset",
                json={"token": raw_token, "password": _VALID_PASSWORD},
            )
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid or expired password reset token"}
        token = SqlAlchemyIdentityActionTokenRepository(db_session).get_by_id(token_id)
        assert token is not None and token.consumed_at is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("status", "deleted"),
    [
        (UserStatus.INACTIVE, False),
        (UserStatus.ACTIVE, True),
    ],
)
def test_password_reset_rejects_inactive_or_deleted_user_without_burning_token(
    db_session: Session,
    status: UserStatus,
    deleted: bool,
) -> None:
    deleted_at = datetime.now(UTC) if deleted else None
    user_id = _seed_account(db_session, status=status, deleted_at=deleted_at)
    raw_token, token_id = _issue_reset_token(
        db_session,
        user_id=user_id,
        clock=MutableClock(datetime.now(UTC)),
        ttl=timedelta(minutes=60),
    )
    client, app = _client_for(db_session)
    try:
        with client:
            response = client.post(
                "/api/v1/auth/password/reset",
                json={"token": raw_token, "password": _VALID_PASSWORD},
            )
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid or expired password reset token"}
        token = SqlAlchemyIdentityActionTokenRepository(db_session).get_by_id(token_id)
        assert token is not None and token.consumed_at is None
    finally:
        app.dependency_overrides.clear()
