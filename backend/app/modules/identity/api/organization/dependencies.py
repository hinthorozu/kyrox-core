from fastapi import Depends

from app.modules.identity.api.authentication.dependencies import (
    get_clock,
    get_id_generator,
    get_user_repository,
)
from app.modules.identity.api.membership.dependencies import (
    get_membership_repository,
    get_organization_repository,
    get_role_repository,
)
from app.modules.identity.application.authentication.id_generator import IdGenerator
from app.modules.identity.application.organization.create_organization import CreateOrganizationUseCase
from app.modules.identity.application.organization.delete_organization import DeleteOrganizationUseCase
from app.modules.identity.application.organization.get_organization import GetOrganizationUseCase
from app.modules.identity.application.organization.list_organizations import ListOrganizationsUseCase
from app.modules.identity.application.organization.suspend_organization import SuspendOrganizationUseCase
from app.modules.identity.application.organization.update_organization import UpdateOrganizationUseCase
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authorization.ports.role_repository import RoleRepository
from app.modules.identity.domain.membership.ports.membership_repository import MembershipRepository
from app.modules.identity.domain.organization.ports.organization_repository import OrganizationRepository


def get_create_organization_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    clock: Clock = Depends(get_clock),
    id_generator: IdGenerator = Depends(get_id_generator),
) -> CreateOrganizationUseCase:
    return CreateOrganizationUseCase(
        organization_repository=organization_repository,
        user_repository=user_repository,
        role_repository=role_repository,
        clock=clock,
        id_generator=id_generator,
    )


def get_list_organizations_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    membership_repository: MembershipRepository = Depends(get_membership_repository),
) -> ListOrganizationsUseCase:
    return ListOrganizationsUseCase(
        organization_repository=organization_repository,
        membership_repository=membership_repository,
    )


def get_get_organization_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> GetOrganizationUseCase:
    return GetOrganizationUseCase(organization_repository=organization_repository)


def get_update_organization_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    clock: Clock = Depends(get_clock),
) -> UpdateOrganizationUseCase:
    return UpdateOrganizationUseCase(
        organization_repository=organization_repository,
        clock=clock,
    )


def get_delete_organization_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> DeleteOrganizationUseCase:
    return DeleteOrganizationUseCase(organization_repository=organization_repository)


def get_suspend_organization_use_case(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    clock: Clock = Depends(get_clock),
) -> SuspendOrganizationUseCase:
    return SuspendOrganizationUseCase(
        organization_repository=organization_repository,
        clock=clock,
    )
