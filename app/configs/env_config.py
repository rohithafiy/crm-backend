import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_UNSET = object()

_is_production = os.getenv("FLASK_ENV", "development").strip().lower() in (
    "production", "prod", "staging"
)


def _require_env(key, fallback=_UNSET):
    val = os.getenv(key)
    if val is None:
        if fallback is _UNSET:
            raise RuntimeError(
                f"CRITICAL: {key} environment variable is not set. "
                "Must be explicitly configured."
            )
        if not _is_production:
            val = fallback
    return val


def _warn_if_http_url(key, url):
    if url.startswith("http://"):
        logger.warning(
            "INSECURE: %s uses plain HTTP (%s). Use HTTPS in production.",
            key, url,
        )


class EnvConfig:
    SECRET_KEY = _require_env("SECRET_KEY")
    JWT_SECRET = _require_env("JWT_SECRET")
    JWT_ACCESS_TOKEN_EXPIRY = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY", "3600"))
    JWT_REFRESH_TOKEN_EXPIRY = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY", "86400"))
    MONGO_URI = _require_env("MONGO_URI")
    MONGO_DB_NAME = _require_env("MONGO_DB_NAME", "lti_crm")
    CLOUDINARY_CLOUD_NAME = _require_env("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = _require_env("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = _require_env("CLOUDINARY_API_SECRET", "")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    RATE_LIMIT_LOGIN_REQUESTS = int(os.getenv("RATE_LIMIT_LOGIN_REQUESTS", "10"))
    RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "300"))
    ACCOUNT_LOCKOUT_THRESHOLD = int(os.getenv("ACCOUNT_LOCKOUT_THRESHOLD", "5"))
    ACCOUNT_LOCKOUT_DURATION = int(os.getenv("ACCOUNT_LOCKOUT_DURATION", "900"))
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    PORTAL1_BASE_URL = _require_env("PORTAL1_BASE_URL", "http://portal1.internal")
    PORTAL1_API_KEY = _require_env("PORTAL1_API_KEY", "")
    PORTAL3_BASE_URL = _require_env("PORTAL3_BASE_URL", "http://portal3.internal")
    PORTAL3_API_KEY = _require_env("PORTAL3_API_KEY", "")
    PORTAL6_BASE_URL = _require_env("PORTAL6_BASE_URL", "http://portal6.internal")
    PORTAL6_API_KEY = _require_env("PORTAL6_API_KEY", "")
    PORTAL8_BASE_URL = _require_env("PORTAL8_BASE_URL", "http://portal8.internal")
    PORTAL8_API_KEY = _require_env("PORTAL8_API_KEY", "")
    PORTAL_WEBHOOK_SECRET = _require_env("PORTAL_WEBHOOK_SECRET", "dev-webhook-secret")
    PORTAL_API_TIMEOUT = int(os.getenv("PORTAL_API_TIMEOUT", "15"))


_warn_if_http_url("PORTAL1_BASE_URL", EnvConfig.PORTAL1_BASE_URL)
_warn_if_http_url("PORTAL3_BASE_URL", EnvConfig.PORTAL3_BASE_URL)
_warn_if_http_url("PORTAL6_BASE_URL", EnvConfig.PORTAL6_BASE_URL)
_warn_if_http_url("PORTAL8_BASE_URL", EnvConfig.PORTAL8_BASE_URL)

if _is_production:
    _portal_keys = [
        ("PORTAL1_API_KEY", EnvConfig.PORTAL1_API_KEY),
        ("PORTAL3_API_KEY", EnvConfig.PORTAL3_API_KEY),
        ("PORTAL6_API_KEY", EnvConfig.PORTAL6_API_KEY),
        ("PORTAL8_API_KEY", EnvConfig.PORTAL8_API_KEY),
    ]
    for key_name, key_val in _portal_keys:
        if not key_val:
            raise RuntimeError(
                f"CRITICAL: {key_name} is empty. "
                "Production deployments must configure portal API keys."
            )
