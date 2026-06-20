"""Role-based access control middleware.

Provides route-level decorators for enforcing role requirements.
Delegates to the core role checking logic in app.utils.role_helper.
"""

from functools import wraps

from flask import g

from app.utils.api_response import forbidden
from app.utils.role_helper import has_any_role, has_role


def require_role(role):
    """Decorator that restricts access to users with a specific role.

    Uses the role hierarchy defined in SecurityConfig, so a super_admin
    inherits access to all roles beneath it.

    Args:
        role: The required role string (e.g. "super_admin", "ops_lead").

    Returns:
        Decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_roles = getattr(g, "roles", [])
            if not has_role(user_roles, role):
                return forbidden(
                    message="Insufficient role",
                    code="INSUFFICIENT_ROLE",
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_roles(roles):
    """Decorator that restricts access to users with any of the specified roles.

    A user only needs ONE of the listed roles to pass the check.
    Role hierarchy is respected.

    Args:
        roles: List of acceptable role strings.

    Returns:
        Decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_roles = getattr(g, "roles", [])
            if not has_any_role(user_roles, roles):
                return forbidden(
                    message="Insufficient role",
                    code="INSUFFICIENT_ROLE",
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator
