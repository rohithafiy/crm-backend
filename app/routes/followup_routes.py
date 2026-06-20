"""
Portal 5 - CRM & Client Management
Follow-up Routes: endpoints for upcoming/today/overdue follow-ups

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request

from app.middleware.auth_middleware import verify_token, require_roles
from app.models.p5_lead import serialize_lead
from app.database.db import get_leads_collection
from app.utils.response_helper import success_response, error_response

logger = logging.getLogger(__name__)

followups_bp = Blueprint("followups", __name__, url_prefix="/api/portal5/followups")


def _serialize_min(lead_doc):
    if not lead_doc:
        return None
    s = serialize_lead(lead_doc)
    return {
        "id": s.get("id"),
        "full_name": s.get("full_name"),
        "company_name": s.get("company_name"),
        "follow_up_date": s.get("follow_up_date"),
        "assigned_to": s.get("assigned_to"),
    }


@followups_bp.route("/today", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def todays_followups():
    today = datetime.now(timezone.utc).date()
    coll = get_leads_collection()
    query = {
        "is_deleted": False,
        "follow_up_date": {"$gte": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc), "$lte": datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)}
    }
    records = list(coll.find(query).sort("follow_up_date", 1))
    payload = [ _serialize_min(r) for r in records ]
    return success_response({"total": len(payload), "followups": payload}, "Follow-ups for today fetched successfully.")


@followups_bp.route("/upcoming", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def upcoming_followups():
    now = datetime.now(timezone.utc)
    coll = get_leads_collection()
    query = {"is_deleted": False, "follow_up_date": {"$gt": now}}
    records = list(coll.find(query).sort("follow_up_date", 1))
    payload = [ _serialize_min(r) for r in records ]
    return success_response({"total": len(payload), "followups": payload}, "Upcoming follow-ups fetched successfully.")


@followups_bp.route("/overdue", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def overdue_followups():
    now = datetime.now(timezone.utc)
    coll = get_leads_collection()
    query = {"is_deleted": False, "follow_up_date": {"$lt": now}}
    records = list(coll.find(query).sort("follow_up_date", 1))
    payload = [ _serialize_min(r) for r in records ]
    return success_response({"total": len(payload), "followups": payload}, "Overdue follow-ups fetched successfully.")
