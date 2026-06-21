from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.configs.env_config import EnvConfig
from app.configs.security_config import SecurityConfig


def create_access_token(user_id, roles_or_role, portals=None):
    now = datetime.now(timezone.utc)
    if isinstance(roles_or_role, list):
        roles = roles_or_role
        role = roles[0] if roles else "client"
    else:
        role = roles_or_role or "client"
        roles = [role]

    payload = {
        "sub": str(user_id),
        "role": role,
        "roles": roles,
        "portals": portals or [],
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=EnvConfig.JWT_ACCESS_TOKEN_EXPIRY),
    }
    encoded = jwt.encode(payload, EnvConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
    return encoded, payload["jti"]



def create_refresh_token(user_id):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=EnvConfig.JWT_REFRESH_TOKEN_EXPIRY),
    }
    encoded = jwt.encode(payload, EnvConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
    return encoded, payload["jti"]


def decode_token(token):
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            EnvConfig.JWT_SECRET,
            algorithms=[SecurityConfig.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "nbf"]},
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_header(request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None
