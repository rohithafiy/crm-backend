"""
Portal 5 - CRM & Client Management
Activity Routes: aggregated activity feed endpoint

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint

from app.middleware.auth_middleware import verify_token
from app.services.activity_service import ActivityService
from app.utils.response_helper import success_response, error_response

logger = logging.getLogger(__name__)

activity_bp = Blueprint("activity", __name__, url_prefix="/api/portal5")


@activity_bp.route("/activity-feed", methods=["GET"])
@verify_token
def activity_feed():
    try:
        limit = 50
        activities = ActivityService.get_activities(limit=limit)
        return success_response({"total": len(activities), "activities": activities}, "Activity feed fetched successfully.")
    except Exception:
        logger.exception("Failed to fetch activity feed")
        return error_response("Internal server error.", 500)
"""
Portal 5 - CRM & Client Management
Activity Routes: REST API endpoints for recent activity feed

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from flask import Blueprint, request
from app.middleware.auth_middleware import verify_token
from app.services.activity_service import ActivityService
from app.utils.response_helper import success_response, error_response

logger = logging.getLogger(__name__)

activity_bp = Blueprint("activity", __name__, url_prefix="/api/portal5/activity-feed")


@activity_bp.route("", methods=["GET"])
@verify_token
def get_activity_feed():
    """
    Get recent aggregated activity feed.

    Query params:
        limit (int, default=50)

    Returns:
        200 with list of activities
    """
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50

    try:
        activities = ActivityService.get_activities(limit=limit)
        return success_response(activities, "Activity feed fetched successfully.")
    except Exception:
        logger.exception("Unexpected error fetching activity feed")
        return error_response("Internal server error.", 500)
