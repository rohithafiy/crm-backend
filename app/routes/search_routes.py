"""
Search Routes: Unified search API for leads/clients/companies/assigned users
"""

import logging

from flask import Blueprint, request

from app.middleware.auth_middleware import verify_token, require_roles
from app.services.search_service import SearchService
from app.utils.pagination_helper import get_pagination_params
from app.utils.response_helper import error_response, paginated_response, success_response

logger = logging.getLogger(__name__)

search_bp = Blueprint("search", __name__, url_prefix="/api/portal5/search")


@search_bp.route("", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def search_all():
    """Query params:
    q (str): search keywords
    target (str): comma-separated targets: leads,clients,companies,assigned_users,all
    page, limit
    """
    q = request.args.get("q", "").strip()
    if not q:
        return error_response("Query parameter 'q' is required.", 400)

    target = request.args.get("target", "all")
    page, limit = get_pagination_params(request)

    try:
        results, total = SearchService.search(q=q, target=target, page=page, limit=limit)
    except Exception:
        logger.exception("Search failed for q=%s target=%s", q, target)
        return error_response("Internal server error.", 500)

    return paginated_response(results, page, limit, total, "Search results fetched.")
