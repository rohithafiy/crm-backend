import time
from collections import defaultdict

from flask import request

from app.configs.env_config import EnvConfig
from app.utils.limiter import limiter

_rate_limit_store = defaultdict(list)
_login_limit_store = defaultdict(list)


def rate_limit_middleware():
    if not EnvConfig.RATE_LIMIT_ENABLED:
        return

    client_ip = request.remote_addr
    now = time.time()

    if request.path == "/api/auth/login":
        window = EnvConfig.RATE_LIMIT_LOGIN_WINDOW
        max_requests = EnvConfig.RATE_LIMIT_LOGIN_REQUESTS
        store = _login_limit_store
    else:
        window = EnvConfig.RATE_LIMIT_WINDOW
        max_requests = EnvConfig.RATE_LIMIT_REQUESTS
        store = _rate_limit_store

    timestamps = store[client_ip]
    store[client_ip] = [t for t in timestamps if now - t < window]

    if len(store[client_ip]) >= max_requests:
        from app.utils.api_response import too_many_requests
        return too_many_requests()

    store[client_ip].append(now)


def register_rate_limit(app):
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from app.utils.api_response import too_many_requests
        return too_many_requests(message="Rate limit exceeded", code="RATE_LIMIT_EXCEEDED")



def log_audit_event(user_id, action, resource, details=None):
    import json
    import logging
    event = {
        "type": "audit",
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "details": details,
    }
    logging.info(json.dumps(event))


def audit_login_attempt(user_id, success, ip_address=None):
    import json
    import logging
    ip = ip_address or request.remote_addr
    event = {
        "type": "audit_login",
        "user_id": user_id,
        "status": "SUCCESS" if success else "FAILED",
        "ip": ip,
    }
    logging.info(json.dumps(event))
