"""
Portal 5 - CRM & Client Management
Response Helper: Standardized API response builders

Author: P5-A2 (CRM Backend Engineer)
"""

from typing import Any, Optional

from flask import jsonify


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[dict] = None,
) -> tuple:
    """
    Build a standardized success response.

    Args:
        data: Response payload
        message: Human-readable message
        status_code: HTTP status code
        meta: Optional metadata (e.g. pagination)

    Returns:
        Flask (response, status_code) tuple
    """
    payload: dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta:
        payload["meta"] = meta

    return jsonify(payload), status_code


def error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[Any] = None,
) -> tuple:
    """
    Build a standardized error response.

    Args:
        message: Human-readable error message
        status_code: HTTP status code
        errors: Optional detailed error list

    Returns:
        Flask (response, status_code) tuple
    """
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors

    return jsonify(payload), status_code


def paginated_response(
    data: list,
    page: int,
    limit: int,
    total_records: int,
    message: str = "Records fetched successfully",
) -> tuple:
    """
    Build a paginated list response.

    Args:
        data: Page of records
        page: Current page number
        limit: Records per page
        total_records: Total matching records
        message: Human-readable message

    Returns:
        Flask (response, status_code) tuple
    """
    import math
    total_pages = math.ceil(total_records / limit) if limit > 0 else 0

    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "current_page": page,
            "page": page,
            "page_size": limit,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
        },
    }), 200
