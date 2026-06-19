from datetime import datetime, timedelta, timezone

import bcrypt
from bson.objectid import ObjectId
from flask import Blueprint, g, request

from app.configs.env_config import EnvConfig
from app.utils import db as _db
from app.utils.api_response import (
    bad_request,
    conflict,
    created,
    forbidden,
    not_found,
    success,
    too_many_requests,
    unauthorized,
)
from app.utils.jwt_helper import create_access_token, create_refresh_token, decode_token
from app.utils.role_helper import validate_role
from app.utils.validation import EMAIL_RULES, LOGIN_RULES, PASSWORD_RULES, validate_request

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
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(EMAIL_RULES + PASSWORD_RULES, data)
    if error:
        return error

    db = _db.get_db()
    existing = db.users.find_one({"email": data["email"]})
    if existing:
        return conflict(message="Email already registered", code="EMAIL_EXISTS")

    password_hash = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()
    roles = data.get("roles", ["client"])
    if not roles or not all(validate_role(r) for r in roles):
        return bad_request(message="Invalid role specified", code="INVALID_ROLE")
    restricted = {"super_admin", "ops_lead"}
    if restricted.intersection(roles):
        return forbidden(
            message="Cannot self-register with elevated role", code="ROLE_RESTRICTED"
        )

    user = {
        "email": data["email"],
        "password_hash": password_hash,
        "roles": roles,
        "portals": _validate_portals(data.get("portals", [])),
        "is_active": True,
    }
    result = db.users.insert_one(user)
    user_id = str(result.inserted_id)

    tokens = _build_token_response(user_id, roles, data.get("portals", []))

    return created(data={
        "user_id": user_id,
        **tokens,
    }, message="User registered successfully")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(LOGIN_RULES, data)
    if error:
        return error

    email = data["email"]
    if _check_account_lockout(email):
        return too_many_requests(
            message="Account temporarily locked due to too many failed attempts",
            code="ACCOUNT_LOCKED",
        )

    db = _db.get_db()
    user = db.users.find_one({"email": email})
    if not user:
        _record_failed_login(email)
        return unauthorized(message="Invalid credentials", code="INVALID_CREDENTIALS")

    if not bcrypt.checkpw(data["password"].encode(), user["password_hash"].encode()):
        _record_failed_login(email)
        return unauthorized(message="Invalid credentials", code="INVALID_CREDENTIALS")

    _clear_login_attempts(email)

    if not user.get("is_active", True):
        return forbidden(message="Account is deactivated", code="ACCOUNT_DEACTIVATED")

    user_id = str(user["_id"])
    tokens = _build_token_response(user_id, user["roles"], user.get("portals", []))

    return success(data={
        "user_id": user_id,
        **tokens,
    }, message="Login successful")


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()
    if not data or not data.get("refresh_token"):
        return bad_request(message="Refresh token required", code="MISSING_FIELD")

    token = data["refresh_token"]
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return unauthorized(message="Invalid refresh token", code="TOKEN_INVALID")

    db = _db.get_db()
    jti = payload.get("jti")
    if db.token_blacklist.find_one({"jti": jti}):
        return unauthorized(message="Token has been revoked", code="TOKEN_REVOKED")

    user = db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        return unauthorized(message="User not found", code="USER_NOT_FOUND")

    if not user.get("is_active", True):
        return forbidden(message="Account is deactivated", code="ACCOUNT_DEACTIVATED")

    db.sessions.update_one({"refresh_jti": jti}, {"$set": {"is_active": False}})
    db.token_blacklist.insert_one({
        "jti": jti,
        "type": "refresh",
        "revoked_at": datetime.now(timezone.utc),
    })

    user_id = str(user["_id"])
    tokens = _build_token_response(user_id, user["roles"], user.get("portals", []))

    return success(data=tokens, message="Token refreshed")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    if not token:
        return bad_request(message="No token provided", code="MISSING_FIELD")

    payload = decode_token(token)
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

    return success(message="Logged out successfully")


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

    return success(message="All sessions terminated")


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
    return success(data=user)


@auth_bp.route("/verify", methods=["GET"])
def verify():
    if not getattr(g, "user_id", None):
        return unauthorized(message="Authentication required")
    return success(data={
        "valid": True,
        "user_id": g.user_id,
        "roles": g.roles,
        "portals": g.portals,
    })
