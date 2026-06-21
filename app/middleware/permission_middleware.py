"""Permission and ownership enforcement middleware.

Provides route-level decorators for checking named permissions
and verifying resource ownership for multi-tenant isolation.
Delegates to the core logic in app.utils.permission_helper.
"""

from app.utils.permission_helper import require_ownership  # noqa: F401
from app.utils.permission_helper import require_permission  # noqa: F401

__all__ = ["require_permission", "require_ownership"]
