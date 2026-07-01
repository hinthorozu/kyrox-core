import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import seed_authenticated_user

from app.modules.identity.infrastructure.persistence.models import UserModel


def seed_super_admin_user(db_session: Session):
    user = seed_authenticated_user(db_session)
    model = db_session.get(UserModel, user.id.value)
    assert model is not None
    model.is_super_admin = True
    model.updated_at = datetime.now(UTC)
    db_session.commit()
    return user
