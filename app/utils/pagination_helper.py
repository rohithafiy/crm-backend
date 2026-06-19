"""
Portal 5 - CRM & Client Management
Pagination Helper: Query param parsing and MongoDB skip/limit helpers

Author: P5-A2 (CRM Backend Engineer)
"""

from typing import Any

from flask import Request


DEFAULT_PAGE = 1
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def get_pagination_params(request: Request) -> tuple[int, int]:
    """
    Extract and validate pagination parameters from request query string.

    Args:
        request: Flask request object

    Returns:
        (page, limit) tuple — both clamped to safe ranges
    """
    try:
        page = int(request.args.get("page", DEFAULT_PAGE))
        page = max(1, page)
    except (ValueError, TypeError):
        page = DEFAULT_PAGE

    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
        limit = max(1, min(limit, MAX_LIMIT))
    except (ValueError, TypeError):
        limit = DEFAULT_LIMIT

    return page, limit


def build_pagination_query(page: int, limit: int) -> tuple[int, int]:
    """
    Compute MongoDB skip and limit values.

    Args:
        page: Current page (1-indexed)
        limit: Records per page

    Returns:
        (skip, limit) tuple for PyMongo
    """
    skip = (page - 1) * limit
    return skip, limit


def get_sort_params(request: Request, default_field: str = "created_at") -> tuple[str, str]:
        """
        Extract sort parameters from the request.

        Query params:
            - `sort` : field name to sort by
            - `order`: 'asc' or 'desc'

        Returns:
            (sort_field, order) where order is 'asc' or 'desc'
        """
        sort_field = request.args.get("sort", default_field)
        order = request.args.get("order", "desc").lower()
        if order not in {"asc", "desc"}:
                order = "desc"
        return sort_field, order
