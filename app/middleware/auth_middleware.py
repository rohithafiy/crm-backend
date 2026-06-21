import logging
from functools import wraps
from typing import Callable, Optional

import jwt
from flask import current_app, g, request

from app.configs.security_config import SecurityConfig
from app.utils import db as _db
from app.utils.api_response import error_response as api_error
from app.utils.jwt_helper import decode_token, get_token_from_header
from app.utils.response_helper import error_response

logger = logging.getLogger(__name__)

ALLOWED_ROLES: set[str] = {"super_admin", "ops_lead", "project_manager"}


# ── Helpers ───────────────────────────────────────────────────────────────

def _is_token_blacklisted(jti):
    try:
        db = _db.get_db()
        return db.token_blacklist.find_one({"jti": jti}) is not None
    except Exception:
        return True


def _extract_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# ── Function-style token verification (used by AuthMiddleware & auth_service) ─

def verify_token():
    token = get_token_from_header(request)
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    jti = payload.get("jti")
    if jti and _is_token_blacklisted(jti):
        return None

    return payload


# ── Middleware class ───────────────────────────────────────────────────────

class AuthMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)

    def before_request(self):
        path = request.path

        if SecurityConfig.is_public_route(path):
            return

        token = get_token_from_header(request) or request.cookies.get("access_token")
        if not token:
            return api_error(message="Authentication required", status_code=401)

        payload = verify_token()
        if not payload:
            return api_error(message="Invalid or expired token", status_code=401)

        g.user_id = payload.get("sub")
        role = payload.get("role")
        roles = payload.get("roles", [])
        if role and role not in roles:
            roles = [role] + roles
        g.roles = roles or ([role] if role else ["client"])
        g.portals = payload.get("portals", [])
        g.token_type = payload.get("type")
        g.token_jti = payload.get("jti")


# ── Decorator-style auth (used by CRM route handlers) ────────────────────

def authenticate(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        token = _extract_token(auth_header)

        if not token:
            return error_response(
                "Authentication required",
                status_code=401,
            )

        secret_key = current_app.config.get("JWT_SECRET_KEY")
        algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")

        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        except jwt.ExpiredSignatureError:
            return error_response("Invalid or expired token", status_code=401)
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid JWT token: %s", str(exc))
            return error_response("Invalid or expired token", status_code=401)

        user_role = payload.get("role", "")
        if user_role not in ALLOWED_ROLES:
            return error_response(
                "You do not have permission to access this resource.",
                status_code=403,
            )

        g.current_user = {
            "user_id": payload.get("user_id") or payload.get("sub"),
            "email": payload.get("email", ""),
            "role": user_role,
            "name": payload.get("name", ""),
        }

        return f(*args, **kwargs)

    return decorated


def require_roles(*roles: str) -> Callable:
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

