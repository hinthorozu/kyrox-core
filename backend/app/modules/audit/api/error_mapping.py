from app.core.exceptions import AppException
from app.modules.audit.domain.exceptions import InvalidAuditEventError
from app.modules.audit.domain.query_exceptions import InvalidAuditQueryError


def map_audit_query_error(exc: InvalidAuditQueryError) -> AppException:
    return AppException(str(exc), status_code=400)


def map_audit_record_error(exc: InvalidAuditEventError) -> AppException:
    return AppException(str(exc), status_code=400)
