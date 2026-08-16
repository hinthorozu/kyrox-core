"""Compatibility import for organization scope validation.

Membership-based access was removed in 20260817_0057. New code must import
assert_organization_scope from app.modules.identity.api.authorization.scope.
"""

from app.modules.identity.api.authorization.scope import assert_organization_scope

__all__ = ["assert_organization_scope"]
