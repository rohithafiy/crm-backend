from datetime import datetime, timezone

from bson.objectid import ObjectId
from flask import Blueprint, g, request

from app.utils import db as _db
from app.utils.api_response import (
    api_response,
    bad_request,
    created,
    not_found,
    paginated,
    success,
)
from app.utils.permission_helper import require_ownership, require_permission
from app.utils.validation import ValidationRule, validate_request

lead_bp = Blueprint("leads", __name__)

LEAD_STATUSES = ["new", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]
LEAD_SOURCES = ["website", "referral", "call", "email", "social", "other"]
LEAD_DEFAULT_STATUS = "new"
LEAD_DEFAULT_SOURCE = "other"

CREATE_RULES = [
    ValidationRule("name", required=True, field_type=str, min_len=1, max_len=200),
    ValidationRule("email", field_type=str, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_len=255),
    ValidationRule("phone", field_type=str, pattern=r"^\+?[\d\s\-\(\)]{7,20}$"),
    ValidationRule("status", field_type=str, enum=LEAD_STATUSES),
    ValidationRule("source", field_type=str, enum=LEAD_SOURCES),
]

UPDATE_RULES = [
    ValidationRule("name", field_type=str, min_len=1, max_len=200),
    ValidationRule("email", field_type=str, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_len=255),
    ValidationRule("phone", field_type=str, pattern=r"^\+?[\d\s\-\(\)]{7,20}$"),
    ValidationRule("status", field_type=str, enum=LEAD_STATUSES),
    ValidationRule("source", field_type=str, enum=LEAD_SOURCES),
]


@lead_bp.route("", methods=["GET"])
@require_permission("leads:read")
@api_response
def list_leads():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    query = {}
    if not g.roles or not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = g.user_id

    total = db.leads.count_documents(query)
    cursor = db.leads.find(query).sort("created_at", -1)
    leads = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for lead in leads:
        lead["_id"] = str(lead["_id"])
    return paginated({"leads": leads}, page, per_page, total)


@lead_bp.route("", methods=["POST"])
@require_permission("leads:write")
@api_response
def create_lead():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(CREATE_RULES, data)
    if error:
        return error

    lead = {
        "name": data["name"],
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "status": data.get("status", LEAD_DEFAULT_STATUS) or LEAD_DEFAULT_STATUS,
        "source": data.get("source", LEAD_DEFAULT_SOURCE) or LEAD_DEFAULT_SOURCE,
        "owner_id": g.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.leads.insert_one(lead)
    lead["_id"] = str(result.inserted_id)
    return created(data={"lead": lead}, message="Lead created")


@lead_bp.route("/<lead_id>", methods=["GET"])
@require_permission("leads:read")
@require_ownership("leads")
@api_response
def get_lead(lead_id):
    db = _db.get_db()
    lead = db.leads.find_one({"_id": ObjectId(lead_id)})
    if not lead:
        return not_found(message="Lead not found")
    lead["_id"] = str(lead["_id"])
    return success(data={"lead": lead})


@lead_bp.route("/<lead_id>", methods=["PUT"])
@require_permission("leads:write")
@require_ownership("leads")
@api_response
def update_lead(lead_id):
    data = request.get_json()
    if not data:
        return bad_request(message="No data provided", code="MISSING_FIELD")

    error = validate_request(UPDATE_RULES, data)
    if error:
        return error

    updates = {k: v for k, v in data.items() if k in ("name", "email", "phone", "status", "source")}
    updates["updated_at"] = datetime.now(timezone.utc)

    db = _db.get_db()
    result = db.leads.update_one({"_id": ObjectId(lead_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Lead not found")

    lead = db.leads.find_one({"_id": ObjectId(lead_id)})
    lead["_id"] = str(lead["_id"])
    return success(data={"lead": lead}, message="Lead updated")


@lead_bp.route("/<lead_id>", methods=["DELETE"])
@require_permission("leads:delete")
@require_ownership("leads")
@api_response
def delete_lead(lead_id):
    db = _db.get_db()
    result = db.leads.delete_one({"_id": ObjectId(lead_id)})
    if result.deleted_count == 0:
        return not_found(message="Lead not found")
    return success(message="Lead deleted")


@lead_bp.route("/<lead_id>/assign", methods=["POST"])
@require_permission("leads:assign")
@api_response
def assign_lead(lead_id):
    data = request.get_json()
    if not data or not data.get("assignee_id"):
        return bad_request(message="Assignee ID required", code="MISSING_FIELD")

    db = _db.get_db()
    result = db.leads.update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": {"assignee_id": data["assignee_id"], "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        return not_found(message="Lead not found")

    lead = db.leads.find_one({"_id": ObjectId(lead_id)})
    lead["_id"] = str(lead["_id"])
    return success(data={"lead": lead}, message="Lead assigned")
