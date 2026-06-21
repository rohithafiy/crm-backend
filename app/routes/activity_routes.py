"""
Portal 5 - CRM & Client Management
Activity Routes: aggregated activity feed endpoint

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint, request

from app.middleware.auth_middleware import authenticate, require_roles
from app.services.activity_service import ActivityService
from app.utils.response_helper import success_response, error_response

logger = logging.getLogger(__name__)

activity_bp = Blueprint("activity", __name__, url_prefix="/api/portal5")


@activity_bp.route("/activity-feed", methods=["GET"])
@authenticate
@require_roles("super_admin", "ops_lead", "project_manager")
def get_activity_feed():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50

    try:
        activities = ActivityService.get_activities(limit=limit)
        return success_response({"total": len(activities), "activities": activities}, "Activity feed fetched successfully.")
    except Exception:
        logger.exception("Failed to fetch activity feed")
        return error_response("Internal server error.", 500)
