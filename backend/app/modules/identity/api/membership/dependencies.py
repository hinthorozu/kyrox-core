from collections.abc import Callable
from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.core.exceptions import AppException
from app.db.session import get_db
from app.modules.identity.api.authentication.dependencies import (
    get_clock,
    get_id_generator,
    get_user_repository,
)
from app.modules.identity.api.authorization.context import (
    AuthenticatedOrganizationContext,
    AuthorizationContext,
)
from app.modules.identity.api.authorization.guards import require_permission
from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.membership.accept_membership_invite import (
    AcceptMembershipInviteUseCase,
)
from app.modules.identity.application.membership.invite_member import InviteMemberUseCase
from app.modules.identity.application.membership.invite_token_issuer import InviteTokenIssuer
from app.modules.identity.application.membership.list_organization_memberships import (
    ListOrganizationMembershipsUseCase,
)
from app.modules.identity.application.membership.role_assignment import MembershipRoleAssigner
from app.modules.identity.application.membership.suspend_membership import (
    RemoveMembershipUseCase,
    SuspendMembershipUseCase,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authorization.ports.organization_role_repository import (
    OrganizationRoleRepository,
)
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
from app.modules.identity.domain.authorization.ports.user_role_repository import UserRoleRepository
from app.modules.identity.api.membership.error_mapping import map_membership_error
from app.modules.identity.domain.membership.exceptions import MembershipNotFoundError
from app.modules.identity.domain.membership.ports.invite_token_service import InviteTokenService
from app.modules.identity.domain.membership.ports.membership_invite_repository import (
    MembershipInviteRepository,
)
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository
from app.modules.identity.infrastructure.authorization.repositories import (
    SqlAlchemyOrganizationRoleRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRoleRepository,
)
from app.modules.identity.infrastructure.membership.repositories import (
    SqlAlchemyMembershipInviteRepository,
    SqlAlchemyMembershipRepository,
)
from app.modules.identity.infrastructure.membership.security.secure_invite_token_service import (
    SecureInviteTokenService,
)
from app.modules.identity.infrastructure.organization.repositories import (
    SqlAlchemyOrganizationRepository,
)


def get_organization_repository(
    db: DbSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> OrganizationRepository:
    return SqlAlchemyOrganizationRepository(db, clock)


def get_membership_repository(
    db: DbSession = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> MembershipRepository:
    return SqlAlchemyMembershipRepository(db, clock)


def get_membership_invite_repository(db: DbSession = Depends(get_db)) -> MembershipInviteRepository:
    return SqlAlchemyMembershipInviteRepository(db)


def get_role_repository(db: DbSession = Depends(get_db)) -> RoleRepository:
    return SqlAlchemyRoleRepository(db)


def get_organization_role_repository(
    db: DbSession = Depends(get_db),
) -> OrganizationRoleRepository:
    return SqlAlchemyOrganizationRoleRepository(db)


def get_user_role_repository(db: DbSession = Depends(get_db)) -> UserRoleRepository:
    return SqlAlchemyUserRoleRepository(db)


def get_membership_role_assigner(
    role_repository: RoleRepository = Depends(get_role_repository),
    organization_role_repository: OrganizationRoleRepository = Depends(get_organization_role_repository),
    user_role_repository: UserRoleRepository = Depends(get_user_role_repository),
    clock: Clock = Depends(get_clock),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> MembershipRoleAssigner:
    return MembershipRoleAssigner(
        role_repository=role_repository,
        organization_role_repository=organization_role_repository,
        user_role_repository=user_role_repository,
        clock=clock,
        id_generator=id_generator,
    )


@lru_cache
def get_invite_token_service() -> InviteTokenService:
    return SecureInviteTokenService()


def get_invite_token_issuer(
    invite_token_service: InviteTokenService = Depends(get_invite_token_service),
) -> InviteTokenIssuer:
    return InviteTokenIssuer(invite_token_service)


def get_list_organization_memberships_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    membership_repository: MembershipRepository = Depends(get_membership_repository),
) -> ListOrganizationMembershipsUseCase:
    return ListOrganizationMembershipsUseCase(
        organization_repository=organization_repository,
        membership_repository=membership_repository,
    )


def get_invite_member_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    membership_invite_repository: MembershipInviteRepository = Depends(get_membership_invite_repository),
    membership_repository: MembershipRepository = Depends(get_membership_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    invite_token_issuer: InviteTokenIssuer = Depends(get_invite_token_issuer),
    clock: Clock = Depends(get_clock),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> InviteMemberUseCase:
    return InviteMemberUseCase(
        organization_repository=organization_repository,
        membership_invite_repository=membership_invite_repository,
        membership_repository=membership_repository,
        user_repository=user_repository,
        invite_token_issuer=invite_token_issuer,
        clock=clock,
        id_generator=id_generator,
    )


def get_accept_membership_invite_use_case(
    membership_invite_repository: MembershipInviteRepository = Depends(get_membership_invite_repository),
    membership_repository: MembershipRepository = Depends(get_membership_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    role_assigner: MembershipRoleAssigner = Depends(get_membership_role_assigner),
    invite_token_issuer: InviteTokenIssuer = Depends(get_invite_token_issuer),
    clock: Clock = Depends(get_clock),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> AcceptMembershipInviteUseCase:
    return AcceptMembershipInviteUseCase(
        membership_invite_repository=membership_invite_repository,
        membership_repository=membership_repository,
        user_repository=user_repository,
        role_assigner=role_assigner,
        invite_token_issuer=invite_token_issuer,
        clock=clock,
        id_generator=id_generator,
    )


def get_suspend_membership_use_case(
    membership_repository: MembershipRepository = Depends(get_membership_repository),
    clock: Clock = Depends(get_clock),
) -> SuspendMembershipUseCase:
    return SuspendMembershipUseCase(
        membership_repository=membership_repository,
        clock=clock,
    )


def get_remove_membership_use_case(
    membership_repository: MembershipRepository = Depends(get_membership_repository),
    clock: Clock = Depends(get_clock),
) -> RemoveMembershipUseCase:
    return RemoveMembershipUseCase(
        membership_repository=membership_repository,
        clock=clock,
    )


def require_scoped_membership(permission_code: str) -> Callable[..., MembershipId]:
    def dependency(
        membership_id: UUID,
        context: AuthorizationContext = Depends(require_permission(permission_code)),
        membership_repository: MembershipRepository = Depends(get_membership_repository),
    ) -> MembershipId:
        membership = membership_repository.get_by_id(MembershipId(membership_id))
        if membership is None or membership.organization_id.value != context.organization_id:
            raise map_membership_error(
                MembershipNotFoundError(f"Membership not found: {membership_id}")
            )
        return MembershipId(membership_id)

    return dependency


def assert_organization_scope(
    path_organization_id: UUID,
    context: AuthorizationContext | AuthenticatedOrganizationContext,
) -> None:
    if path_organization_id != context.organization_id:
        raise AppException("Organization scope mismatch", status_code=400)
