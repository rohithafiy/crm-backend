from datetime import datetime, timedelta, timezone

import bcrypt
from bson.objectid import ObjectId
from flask import Blueprint, g, make_response, request

from app.configs.env_config import EnvConfig
from app.middleware.auth_middleware import verify_token
from app.utils import db as _db
from app.utils.api_response import (
    bad_request,
    forbidden,
    not_found,
    success,
    too_many_requests,
    unauthorized,
)
from app.utils.jwt_helper import create_access_token, create_refresh_token, decode_token
from app.utils.role_helper import validate_role
from app.utils.validation import EMAIL_RULES, LOGIN_RULES, validate_request
from app.utils.limiter import limiter
from app.utils.audit_helper import log_audit

auth_bp = Blueprint("auth", __name__)

_LOCKOUT_CACHE = {}


def _check_account_lockout(email):
    entry = _LOCKOUT_CACHE.get(email)
    if not entry:
        return False
    if datetime.now(timezone.utc) > entry["locked_until"]:
        del _LOCKOUT_CACHE[email]
        return False
    return True


def _record_failed_login(email):
    now = datetime.now(timezone.utc)
    entry = _LOCKOUT_CACHE.setdefault(email, {"attempts": 0, "locked_until": now})
    entry["attempts"] += 1
    if entry["attempts"] >= EnvConfig.ACCOUNT_LOCKOUT_THRESHOLD:
        entry["locked_until"] = now + timedelta(seconds=EnvConfig.ACCOUNT_LOCKOUT_DURATION)


def _clear_login_attempts(email):
    _LOCKOUT_CACHE.pop(email, None)


def _validate_portals(portals):
    valid_portals = {"portal1", "portal3", "portal5", "portal6", "portal8"}
    if isinstance(portals, list):
        return [p for p in portals if p in valid_portals]
    return []


def _set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        "access_token", access_token,
        httponly=True, secure=True, samesite="Strict",
        max_age=EnvConfig.JWT_ACCESS_TOKEN_EXPIRY,
        path="/",
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, secure=True, samesite="Strict",
        max_age=EnvConfig.JWT_REFRESH_TOKEN_EXPIRY,
        path="/api/auth",
    )


def _clear_auth_cookies(response):
    response.set_cookie("access_token", "", httponly=True, secure=True, samesite="Strict", max_age=0, path="/")
    response.set_cookie("refresh_token", "", httponly=True, secure=True, samesite="Strict", max_age=0, path="/api/auth")


def _build_token_response(user_id, roles, portals):
    access_token, access_jti = create_access_token(user_id, roles, portals)
    refresh_token, refresh_jti = create_refresh_token(user_id)
    now = datetime.now(timezone.utc)
    db = _db.get_db()
    db.sessions.insert_one({
        "user_id": user_id,
        "access_jti": access_jti,
        "refresh_jti": refresh_jti,
        "created_at": now,
        "expires_at": now + timedelta(seconds=EnvConfig.JWT_REFRESH_TOKEN_EXPIRY),
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
        "is_active": True,
    })
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"last_login": now}})
    return access_token, refresh_token


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(LOGIN_RULES, data)
    if error:
        return error

    email = data["email"]
    if _check_account_lockout(email):
        log_audit(email, "login_failure", "auth", {"reason": "account_locked", "ip_address": request.remote_addr})
        return too_many_requests(
            message="Account temporarily locked due to too many failed attempts",
            code="ACCOUNT_LOCKED",
        )

    db = _db.get_db()
    user = db.users.find_one({"email": email})
    if not user:
        _record_failed_login(email)
        log_audit(email, "login_failure", "auth", {"reason": "user_not_found", "ip_address": request.remote_addr})
        return unauthorized(message="Invalid credentials")

    if not bcrypt.checkpw(data["password"].encode(), user["password_hash"].encode()):
        _record_failed_login(email)
        log_audit(email, "login_failure", "auth", {"reason": "incorrect_password", "ip_address": request.remote_addr})
        return unauthorized(message="Invalid credentials")

    _clear_login_attempts(email)

    if not user.get("is_active", True):
        log_audit(str(user["_id"]), "login_failure", "auth", {"reason": "account_deactivated", "ip_address": request.remote_addr})
        return forbidden(message="Account is deactivated", code="ACCOUNT_DEACTIVATED")

    user_id = str(user["_id"])
    
    # Align role/roles schema
    role = user.get("role")
    roles = user.get("roles", [])
    if role and not roles:
        roles = [role]
    elif roles and not role:
        role = roles[0]

    access_token, refresh_token = _build_token_response(user_id, roles, user.get("portals", []))

    resp = make_response(success(message="Login successful"))
    _set_auth_cookies(resp, access_token, refresh_token)
    log_audit(user_id, "login_success", "auth", {"ip_address": request.remote_addr})
    return resp


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("5 per minute")
def refresh():
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        from app.utils.api_response import error_response
        log_audit("anonymous", "token_refresh_failure", "auth", {"reason": "missing_cookie"})
        return error_response(message="Invalid or expired token", status_code=401)

    payload = decode_token(refresh_token_cookie)
    if not payload or payload.get("type") != "refresh":
        from app.utils.api_response import error_response
        log_audit("anonymous", "token_refresh_failure", "auth", {"reason": "invalid_payload"})
        return error_response(message="Invalid or expired token", status_code=401)

    db = _db.get_db()
    jti = payload.get("jti")
    if db.token_blacklist.find_one({"jti": jti}):
        from app.utils.api_response import error_response
        log_audit(payload.get("sub", "unknown"), "token_refresh_failure", "auth", {"reason": "token_blacklisted"})
        return error_response(message="Invalid or expired token", status_code=401)

    user = db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        from app.utils.api_response import error_response
        log_audit(payload.get("sub", "unknown"), "token_refresh_failure", "auth", {"reason": "user_not_found"})
        return error_response(message="Invalid or expired token", status_code=401)

    if not user.get("is_active", True):
        from app.utils.api_response import error_response
        log_audit(str(user["_id"]), "token_refresh_failure", "auth", {"reason": "user_inactive"})
        return error_response(message="Invalid or expired token", status_code=401)

    db.sessions.update_one({"refresh_jti": jti}, {"$set": {"is_active": False}})
    db.token_blacklist.insert_one({
        "jti": jti,
        "type": "refresh",
        "revoked_at": datetime.now(timezone.utc),
    })

    user_id = str(user["_id"])
    role = user.get("role")
    roles = user.get("roles", [])
    if role and not roles:
        roles = [role]
    elif roles and not role:
        role = roles[0]

    access_token, new_refresh_token = _build_token_response(user_id, roles, user.get("portals", []))

    resp = make_response(success(message="Token refreshed"))
    _set_auth_cookies(resp, access_token, new_refresh_token)
    log_audit(user_id, "token_refresh_success", "auth")
    return resp


@auth_bp.route("/logout", methods=["POST"])
def logout():
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        resp = make_response(success(message="Logged out successfully"))
        _clear_auth_cookies(resp)
        log_audit("anonymous", "logout", "auth")
        return resp

    payload = decode_token(token)
    user_id = "unknown"
    if payload:
        jti = payload.get("jti")
        user_id = payload.get("sub")
        db = _db.get_db()
        db.token_blacklist.insert_one({
            "jti": jti,
            "type": payload.get("type", "access"),
            "user_id": user_id,
            "revoked_at": datetime.now(timezone.utc),
        })
        db.sessions.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}},
        )

    resp = make_response(success(message="Logged out successfully"))
    _clear_auth_cookies(resp)
    log_audit(user_id, "logout", "auth")
    return resp


@auth_bp.route("/logout/all", methods=["POST"])
def logout_all():
    if not getattr(g, "user_id", None):
        return unauthorized(message="Authentication required")

    user_id = g.user_id
    db = _db.get_db()
    sessions = db.sessions.find({"user_id": user_id, "is_active": True})
    for session in sessions:
        for jti_field in ("access_jti", "refresh_jti"):
            jti = session.get(jti_field)
            if jti:
                db.token_blacklist.insert_one({
                    "jti": jti,
                    "type": "session",
                    "user_id": user_id,
                    "revoked_at": datetime.now(timezone.utc),
                })

    db.sessions.update_many(
        {"user_id": user_id, "is_active": True},
        {"$set": {"is_active": False}},
    )

    resp = make_response(success(message="All sessions terminated"))
    _clear_auth_cookies(resp)
    return resp


@auth_bp.route("/sessions", methods=["GET"])
def list_sessions():
    if not getattr(g, "user_id", None):
        return unauthorized(message="Authentication required")

    db = _db.get_db()
    projection = {
        "_id": 1, "created_at": 1, "expires_at": 1,
        "ip_address": 1, "user_agent": 1, "is_active": 1,
    }
    sessions = list(db.sessions.find(
        {"user_id": g.user_id}, projection
    ).sort("created_at", -1))

    for s in sessions:
        s["_id"] = str(s["_id"])
        s["created_at"] = s["created_at"].isoformat() if s.get("created_at") else None
        s["expires_at"] = s["expires_at"].isoformat() if s.get("expires_at") else None

    return success(data={"sessions": sessions})


@auth_bp.route("/sessions/<session_id>", methods=["DELETE"])
def revoke_session(session_id):
    if not getattr(g, "user_id", None):
        return unauthorized(message="Authentication required")

    db = _db.get_db()
    session = db.sessions.find_one({"_id": ObjectId(session_id), "user_id": g.user_id})
    if not session:
        return not_found(message="Session not found")

    for jti_field in ("access_jti", "refresh_jti"):
        jti = session.get(jti_field)
        if jti:
            db.token_blacklist.insert_one({
                "jti": jti,
                "type": "session_revoked",
                "user_id": g.user_id,
                "revoked_at": datetime.now(timezone.utc),
            })

    db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"is_active": False}})
    return success(message="Session revoked")


@auth_bp.route("/me", methods=["GET"])
def me():
    if not getattr(g, "user_id", None):
        return unauthorized(message="Authentication required")
    db = _db.get_db()
    user = db.users.find_one({"_id": ObjectId(g.user_id)}, {"password_hash": 0})
    if not user:
        return not_found(message="User not found")
    user["_id"] = str(user["_id"])
    return success(data=user, message="User retrieved")


@auth_bp.route("/verify", methods=["GET"])
def verify():
    payload = verify_token()
    if not payload:
        return unauthorized(message="Invalid or expired token")
    return success(data={
        "valid": True,
        "user_id": payload.get("sub"),
        "roles": payload.get("roles", []),
        "portals": payload.get("portals", []),
    })
