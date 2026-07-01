class MembershipError(Exception):
    """Base class for membership domain failures."""


class MembershipNotFoundError(MembershipError):
    """Membership lookup failed."""


class DuplicateMembershipError(MembershipError):
    """User is already linked to the organization."""


class InvalidMembershipTransitionError(MembershipError):
    """Membership status transition is not allowed."""


class MembershipInviteExpiredError(MembershipError):
    """Membership invite has expired."""


class MembershipInviteAlreadyAcceptedError(MembershipError):
    """Membership invite was already accepted."""
