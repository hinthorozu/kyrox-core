import pytest
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)


@pytest.mark.parametrize(
    ("enum_cls", "expected"),
    [
        (UserStatus, ("active", "inactive", "suspended")),
        (OrganizationStatus, ("active", "inactive", "suspended")),
        (MembershipStatus, ("active", "inactive", "suspended")),
    ],
)
def test_status_enums_expose_expected_values(enum_cls, expected) -> None:
    assert tuple(member.value for member in enum_cls) == expected


def test_status_enums_are_str_enums() -> None:
    assert UserStatus.ACTIVE == "active"
    assert OrganizationStatus.SUSPENDED == "suspended"
    assert MembershipStatus.INACTIVE == "inactive"
