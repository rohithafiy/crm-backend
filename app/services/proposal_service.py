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

proposal_bp = Blueprint("proposals", __name__)

PROPOSAL_STATUSES = ["draft", "sent", "reviewing", "accepted", "rejected", "cancelled"]

CREATE_RULES = [
    ValidationRule("title", required=True, field_type=str, min_len=1, max_len=300),
    ValidationRule("client_id", required=True, field_type=str),
    ValidationRule("amount", field_type=(int, float), min_value=0),
    ValidationRule("status", field_type=str, enum=PROPOSAL_STATUSES),
    ValidationRule("description", field_type=str, max_len=5000),
]

UPDATE_RULES = [
    ValidationRule("title", field_type=str, min_len=1, max_len=300),
    ValidationRule("amount", field_type=(int, float), min_value=0),
    ValidationRule("status", field_type=str, enum=PROPOSAL_STATUSES),
    ValidationRule("description", field_type=str, max_len=5000),
]


@proposal_bp.route("", methods=["GET"])
@require_permission("proposals:read")
@api_response
def list_proposals():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    query = {}
    if not g.roles or not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = g.user_id

    total = db.proposals.count_documents(query)
    cursor = db.proposals.find(query).sort("created_at", -1)
    proposals = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for p in proposals:
        p["_id"] = str(p["_id"])
    return paginated({"proposals": proposals}, page, per_page, total)


@proposal_bp.route("", methods=["POST"])
@require_permission("proposals:write")
@api_response
def create_proposal():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(CREATE_RULES, data)
    if error:
        return error

    proposal = {
        "title": data["title"],
        "client_id": data["client_id"],
        "amount": data.get("amount", 0),
        "status": data.get("status", "draft"),
        "description": data.get("description", ""),
        "owner_id": g.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.proposals.insert_one(proposal)
    proposal["_id"] = str(result.inserted_id)
    return created(data={"proposal": proposal}, message="Proposal created")


@proposal_bp.route("/<proposal_id>", methods=["GET"])
@require_permission("proposals:read")
@require_ownership("proposals")
@api_response
def get_proposal(proposal_id):
    db = _db.get_db()
    proposal = db.proposals.find_one({"_id": ObjectId(proposal_id)})
    if not proposal:
        return not_found(message="Proposal not found")
    proposal["_id"] = str(proposal["_id"])
    return success(data={"proposal": proposal})


@proposal_bp.route("/<proposal_id>", methods=["PUT"])
@require_permission("proposals:write")
@require_ownership("proposals")
@api_response
def update_proposal(proposal_id):
    data = request.get_json()
    if not data:
        return bad_request(message="No data provided", code="MISSING_FIELD")

    error = validate_request(UPDATE_RULES, data)
    if error:
        return error

    updates = {k: v for k, v in data.items() if k in ("title", "amount", "status", "description")}
    updates["updated_at"] = datetime.now(timezone.utc)

    db = _db.get_db()
    result = db.proposals.update_one({"_id": ObjectId(proposal_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Proposal not found")

    proposal = db.proposals.find_one({"_id": ObjectId(proposal_id)})
    proposal["_id"] = str(proposal["_id"])
    return success(data={"proposal": proposal}, message="Proposal updated")


@proposal_bp.route("/<proposal_id>", methods=["DELETE"])
@require_permission("proposals:delete")
@require_ownership("proposals")
@api_response
def delete_proposal(proposal_id):
    db = _db.get_db()
    result = db.proposals.delete_one({"_id": ObjectId(proposal_id)})
    if result.deleted_count == 0:
        return not_found(message="Proposal not found")
    return success(message="Proposal deleted")


@proposal_bp.route("/<proposal_id>/approve", methods=["POST"])
@require_permission("proposals:approve")
@api_response
def approve_proposal(proposal_id):
    db = _db.get_db()
    result = db.proposals.update_one(
        {"_id": ObjectId(proposal_id)},
        {
            "$set": {
                "status": "accepted",
                "approved_by": g.user_id,
                "approved_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        return not_found(message="Proposal not found")

    proposal = db.proposals.find_one({"_id": ObjectId(proposal_id)})
    proposal["_id"] = str(proposal["_id"])
    return success(data={"proposal": proposal}, message="Proposal approved")
