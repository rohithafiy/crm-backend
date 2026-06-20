from flask import g, request

from app.configs.security_config import SecurityConfig
from app.utils import db as _db
from app.utils.jwt_helper import decode_token, get_token_from_header


def _is_token_blacklisted(jti):
    try:
        db = _db.get_db()
        return db.token_blacklist.find_one({"jti": jti}) is not None
    except Exception:
        return True


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
            from app.utils.api_response import error_response
            return error_response(message="Authentication required", status_code=401)

        payload = verify_token()
        if not payload:
            from app.utils.api_response import error_response
            return error_response(message="Invalid or expired token", status_code=401)

        g.user_id = payload.get("sub")
        role = payload.get("role")
        roles = payload.get("roles", [])
        if role and role not in roles:
            roles = [role] + roles
        g.roles = roles or ([role] if role else ["client"])
        g.portals = payload.get("portals", [])
        g.token_type = payload.get("type")
        g.token_jti = payload.get("jti")

