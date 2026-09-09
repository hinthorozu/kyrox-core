from app.modules.jobs.application.worker.fair_crm_lifecycle_handler import (
    FairCrmSuspensionSecuritySignalHandler,
)
from app.modules.jobs.application.worker.registry import InMemoryJobHandlerRegistry
from app.modules.jobs.application.worker.stub_handlers import EchoJobHandler
from app.modules.jobs.domain.value_objects.job_type import JobType


def build_job_handler_registry() -> InMemoryJobHandlerRegistry:
    registry = InMemoryJobHandlerRegistry()
    registry.register(JobType.create("core.platform.echo"), EchoJobHandler())
    registry.register(
        JobType.create("core.identity.organization_suspended"),
        FairCrmSuspensionSecuritySignalHandler(),
    )
    return registry