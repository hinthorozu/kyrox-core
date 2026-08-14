"""Compatibility export for the canonical identity Super Admin guard."""

from app.modules.identity.api.authorization.guards import require_super_admin

__all__ = ["require_super_admin"]
