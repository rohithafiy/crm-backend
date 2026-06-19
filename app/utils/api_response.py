import logging
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, request

logger = logging.getLogger(__name__)

API_VERSION = "v1"
API_VENDOR = "lti-crm"


def _metadata():
    return {
        "api_version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _extract_request_id():
    return request.headers.get("X-Request-Id", "")


# ─── Success Responses ───────────────────────────────────────────────────────


def success(data=None, message=None, status_code=200):
    body = {
        "status": "success",
        "code": status_code,
        "data": data,
        "metadata": _metadata(),
    }
    if message:
        body["message"] = message
    return jsonify(body), status_code


def created(data=None, message="Resource created"):
    return success(data, message, 201)


def paginated(data, page, per_page, total, **extra):
    total_pages = max(1, (total + per_page - 1) // per_page)
    return jsonify({
        "status": "success",
        "code": 200,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        "metadata": _metadata(),
    }), 200, {"X-Total-Count": str(total)}


# ─── Error Responses ─────────────────────────────────────────────────────────


def _error(status_code, error_type, error_code, message, details=None):
    return jsonify({
        "status": "error",
        "code": status_code,
        "error": {
            "type": error_type,
            "code": error_code,
            "message": message,
            "details": details or {},
        },
        "metadata": _metadata(),
    }), status_code


def bad_request(message="Bad request", code="VALIDATION_ERROR", details=None):
    return _error(400, "validation_error", code, message, details)


def unauthorized(message="Authentication required", code="TOKEN_MISSING", details=None):
    return _error(401, "authentication_error", code, message, details)


def forbidden(message="Insufficient permissions", code="INSUFFICIENT_PERMISSIONS", details=None):
    return _error(403, "authorization_error", code, message, details)


def not_found(message="Resource not found", code="RESOURCE_NOT_FOUND", details=None):
    return _error(404, "not_found", code, message, details)


def conflict(message="Resource already exists", code="RESOURCE_CONFLICT", details=None):
    return _error(409, "conflict", code, message, details)


def too_many_requests(message="Rate limit exceeded", code="RATE_LIMIT_EXCEEDED", details=None):
    return _error(429, "rate_limit", code, message, details)


def internal_error(message="Internal server error", code="INTERNAL_ERROR", details=None):
    return _error(500, "system_error", code, message, details)


# ─── Response Wrapper Decorator ──────────────────────────────────────────────


def api_response(f):
    """Wraps route handlers to catch errors and standardize responses."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                return result
            if result is None:
                return success()
            if isinstance(result, dict):
                return success(result)
            if isinstance(result, list):
                return success(result)
            return result
        except Exception:
            logger.exception("Unhandled exception in route handler")
            return internal_error(message="An internal error occurred", code="INTERNAL_ERROR")

    return wrapper
