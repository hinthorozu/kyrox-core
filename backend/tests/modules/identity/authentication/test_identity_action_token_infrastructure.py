import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.clock import UtcClock
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_identity_action_token_repository import (
    SqlAlchemyIdentityActionTokenRepository,
)
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _create_user(db_session: Session) -> User:
    now = _now()
    repository = SqlAlchemyUserRepository(db_session, UtcClock())
    user = repository.add(
        User(
            id=UserId(uuid.UUID("00000000-0000-0000-0000-000000000777")),
            email=Email.create("action-token@example.com"),
            password_hash=PasswordHash("hash"),
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.flush()
    return user


def _token(
    user_id: UserId,
    *,
    token_id: int,
    token_hash: str,
    purpose: IdentityActionTokenPurpose,
) -> IdentityActionToken:
    now = _now()
    return IdentityActionToken(
        id=IdentityActionTokenId(uuid.UUID(int=token_id)),
        user_id=user_id,
        purpose=purpose,
        token_hash=TokenHash(token_hash),
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )


def test_repository_atomic_consume_allows_only_one_success(db_session: Session) -> None:
    user = _create_user(db_session)
    repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_hash = TokenHash("a" * 64)
    repository.add(
        _token(
            user.id,
            token_id=1,
            token_hash=token_hash.value,
            purpose=IdentityActionTokenPurpose.PASSWORD_RESET,
        )
    )
    db_session.commit()

    first = repository.consume_if_available(
        token_hash,
        IdentityActionTokenPurpose.PASSWORD_RESET,
        _now(),
    )
    second = repository.consume_if_available(
        token_hash,
        IdentityActionTokenPurpose.PASSWORD_RESET,
        _now(),
    )

    assert first is not None
    assert first.consumed_at is not None
    assert second is None


def test_repository_wrong_purpose_does_not_consume(db_session: Session) -> None:
    user = _create_user(db_session)
    repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    token_hash = TokenHash("b" * 64)
    repository.add(
        _token(
            user.id,
            token_id=2,
            token_hash=token_hash.value,
            purpose=IdentityActionTokenPurpose.PASSWORD_RESET,
        )
    )
    db_session.commit()

    consumed = repository.consume_if_available(
        token_hash,
        IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
        _now(),
    )
    loaded = repository.get_by_token_hash(token_hash)

    assert consumed is None
    assert loaded is not None
    assert loaded.consumed_at is None


def test_repository_supersedes_only_matching_user_and_purpose(db_session: Session) -> None:
    user = _create_user(db_session)
    repository = SqlAlchemyIdentityActionTokenRepository(db_session)
    reset_hash = TokenHash("c" * 64)
    activation_hash = TokenHash("d" * 64)
    repository.add(
        _token(
            user.id,
            token_id=3,
            token_hash=reset_hash.value,
            purpose=IdentityActionTokenPurpose.PASSWORD_RESET,
        )
    )
    repository.add(
        _token(
            user.id,
            token_id=4,
            token_hash=activation_hash.value,
            purpose=IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
        )
    )
    db_session.commit()

    count = repository.invalidate_outstanding_for_user_purpose(
        user.id,
        IdentityActionTokenPurpose.PASSWORD_RESET,
        _now(),
    )
    reset = repository.get_by_token_hash(reset_hash)
    activation = repository.get_by_token_hash(activation_hash)

    assert count == 1
    assert reset is not None and reset.invalidated_at is not None
    assert activation is not None and activation.invalidated_at is None
