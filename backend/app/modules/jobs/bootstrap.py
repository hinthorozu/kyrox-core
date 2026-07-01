from app.modules.jobs.application.worker.registry import InMemoryJobHandlerRegistry
from app.modules.jobs.application.worker.stub_handlers import EchoJobHandler
from app.modules.jobs.domain.value_objects.job_type import JobType


def build_job_handler_registry() -> InMemoryJobHandlerRegistry:
    registry = InMemoryJobHandlerRegistry()
    registry.register(JobType.create("core.platform.echo"), EchoJobHandler())
    return registry
