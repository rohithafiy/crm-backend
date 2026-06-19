"""
Portal 5 - CRM & Client Management
Auth Middleware: JWT verification and RBAC decorator

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from functools import wraps
from typing import Callable, Optional

import jwt
from flask import current_app, g, request

from app.utils.response_helper import error_response

logger = logging.getLogger(__name__)

ALLOWED_ROLES: set[str] = {"super_admin", "ops_lead", "project_manager"}


def _extract_token(auth_header: Optional[str]) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.

    Args:
        auth_header: Value of the Authorization header

    Returns:
        Token string or None
    """
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def verify_token(f: Callable) -> Callable:
    """
    Decorator: validate JWT and enforce role-based access.

    Attaches decoded payload to Flask's ``g.current_user``.

    Usage::

        @blueprint.route("/resource")
        @verify_token
        def resource():
            user = g.current_user
            ...

    Returns 401 for missing/invalid token, 403 for insufficient role.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = _extract_token(auth_header)

        if not token:
            return error_response(
                "Authorization token is missing.",
                status_code=401,
            )

        secret_key = current_app.config.get("JWT_SECRET_KEY")
        algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")

        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        except jwt.ExpiredSignatureError:
            return error_response("Token has expired.", status_code=401)
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid JWT token: %s", str(exc))
            return error_response("Invalid authentication token.", status_code=401)

        user_role = payload.get("role", "")
        if user_role not in ALLOWED_ROLES:
            return error_response(
                "You do not have permission to access this resource.",
                status_code=403,
            )

        # Attach user context for downstream use
        g.current_user = {
            "user_id": payload.get("user_id") or payload.get("sub"),
            "email": payload.get("email", ""),
            "role": user_role,
            "name": payload.get("name", ""),
        }

        return f(*args, **kwargs)

    return decorated


def require_roles(*roles: str) -> Callable:
    """
    Decorator factory: restrict access to specific roles only.

    Usage::

        @blueprint.route("/admin-only")
        @verify_token
        @require_roles("super_admin")
        def admin_only():
            ...

    Args:
        *roles: Allowed role strings

    Returns:
        Decorator function
    """
    allowed = set(roles)

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = getattr(g, "current_user", {})
            if current_user.get("role") not in allowed:
                return error_response(
                    "Insufficient permissions for this action.",
                    status_code=403,
                )
            return f(*args, **kwargs)

        return decorated

    return decorator
