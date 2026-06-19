import hashlib
import hmac
import logging
from datetime import datetime, timezone
from enum import Enum

import requests

from app.configs.env_config import EnvConfig


class PortalID(Enum):
    PORTAL_1 = "portal1"
    PORTAL_3 = "portal3"
    PORTAL_6 = "portal6"
    PORTAL_8 = "portal8"


PORTAL_CONFIG = {
    PortalID.PORTAL_1: {
        "base_url": EnvConfig.PORTAL1_BASE_URL,
        "api_key": EnvConfig.PORTAL1_API_KEY,
    },
    PortalID.PORTAL_3: {
        "base_url": EnvConfig.PORTAL3_BASE_URL,
        "api_key": EnvConfig.PORTAL3_API_KEY,
    },
    PortalID.PORTAL_6: {
        "base_url": EnvConfig.PORTAL6_BASE_URL,
        "api_key": EnvConfig.PORTAL6_API_KEY,
    },
    PortalID.PORTAL_8: {
        "base_url": EnvConfig.PORTAL8_BASE_URL,
        "api_key": EnvConfig.PORTAL8_API_KEY,
    },
}

_portal_registry = {}
logger = logging.getLogger(__name__)


def register_portal(name, blueprint_or_routes):
    _portal_registry[name] = blueprint_or_routes


def get_registered_portals():
    return list(_portal_registry.keys())


def sign_webhook_payload(payload, secret):
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(payload, signature, secret):
    expected = sign_webhook_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def register_portal_routes(app):
    for name, bp in _portal_registry.items():
        app.register_blueprint(bp, url_prefix=f"/portal/{name}")


def _call_portal_api(portal, method, path, json_data=None, params=None):
    """Core HTTP client for cross-portal API calls.
    Portal 5 NEVER accesses other portal databases directly.
    All communication goes through HTTP APIs only.
    """
    config = PORTAL_CONFIG.get(portal)
    if not config:
        raise ValueError(f"Unknown portal: {portal}")

    url = f"{config['base_url'].rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "X-Portal-5-Auth": config["api_key"],
        "X-Portal-Name": "portal5",
        "X-Request-Timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload_body = ""
    if json_data:
        import json
        payload_body = json.dumps(json_data, default=str)

    if payload_body:
        headers["X-Webhook-Signature"] = sign_webhook_payload(
            payload_body, EnvConfig.PORTAL_WEBHOOK_SECRET
        )

    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
            timeout=EnvConfig.PORTAL_API_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.Timeout:
        logger.error(f"Timeout calling {portal.value} API: {method} {url}")
        raise
    except requests.RequestException as e:
        logger.error(f"Error calling {portal.value} API: {method} {url} - {e}")
        raise


def call_portal_api(portal, method, path, json_data=None, params=None):
    """Public wrapper with retry logic."""
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            return _call_portal_api(portal, method, path, json_data, params)
        except requests.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
    raise last_error
