from flask import g, request

from app.configs.security_config import SecurityConfig
from app.utils import db as _db
from app.utils.api_response import unauthorized
from app.utils.jwt_helper import decode_token, get_token_from_header


def _is_token_blacklisted(jti):
    try:
        db = _db.get_db()
        return db.token_blacklist.find_one({"jti": jti}) is not None
    except Exception:
        return True


class AuthMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)

    def before_request(self):
        path = request.path

        if SecurityConfig.is_public_route(path):
            return

        token = get_token_from_header(request)
        if not token:
            return unauthorized(
                message="Missing authorization token", code="TOKEN_MISSING"
            )

        payload = decode_token(token)
        if not payload:
            return unauthorized(
                message="Invalid or expired token", code="TOKEN_INVALID"
            )

        if payload.get("type") != "access":
            return unauthorized(
                message="Invalid token type", code="TOKEN_TYPE_INVALID"
            )

        jti = payload.get("jti")
        if jti and _is_token_blacklisted(jti):
            return unauthorized(
                message="Token has been revoked", code="TOKEN_REVOKED"
            )

        g.user_id = payload.get("sub")
        g.roles = payload.get("roles", [])
        g.portals = payload.get("portals", [])
        g.token_type = payload.get("type")
        g.token_jti = jti
