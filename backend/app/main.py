from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.modules.jobs.application.commands import ProcessPendingJobsCommand
from app.modules.jobs.application.policy import JobPolicy
from app.modules.jobs.application.process_pending_jobs import ProcessPendingJobsUseCase
from app.modules.jobs.bootstrap import build_job_handler_registry
from app.modules.notifications.bootstrap import register_notification_platform
from app.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        use_case = ProcessPendingJobsUseCase(
            job_repository=SqlAlchemyJobRepository(db),
            handler_registry=app.state.job_handler_registry,
            job_policy=JobPolicy(),
        )
        use_case.execute(ProcessPendingJobsCommand(limit=JobPolicy().default_batch_size))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.state.job_handler_registry = build_job_handler_registry()
    app.state.notification_channel_registry = register_notification_platform(
        app.state.job_handler_registry
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
