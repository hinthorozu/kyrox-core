from __future__ import annotations

from uuid import UUID

import httpx

from app.core.config import settings
from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.ports import JobHandlerResult


class FairCrmSuspensionSecuritySignalHandler:
    """Deliver the durable OL09-B suspension security signal to FAIR CRM."""

    def handle(self, job: Job) -> JobHandlerResult:
        signal_token = settings.FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN
        if signal_token is None or not signal_token.strip():
            raise RuntimeError("FAIR CRM lifecycle signal credential is not configured")

        organization_id = UUID(str(job.payload["organization_id"]))
        lifecycle_updated_at = str(job.payload["lifecycle_updated_at"])
        url = (
            f"{settings.FAIR_CRM_BASE_URL.rstrip('/')}"
            "/api/v1/internal/lifecycle-security/organization-suspended"
        )
        headers = {
            "X-Kyrox-Lifecycle-Signal-Token": signal_token,
            "Accept": "application/json",
        }
        payload = {
            "organization_id": str(organization_id),
            "lifecycle_updated_at": lifecycle_updated_at,
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                "FAIR CRM suspension security signal failed: "
                f"status={response.status_code}"
            )

        return JobHandlerResult(
            result={
                "delivered": True,
                "organization_id": str(organization_id),
                "lifecycle_updated_at": lifecycle_updated_at,
            }
        )
