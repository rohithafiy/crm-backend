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

client_bp = Blueprint("clients", __name__)

CREATE_RULES = [
    ValidationRule("name", required=True, field_type=str, min_len=1, max_len=200),
    ValidationRule("email", field_type=str, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_len=255),
    ValidationRule("phone", field_type=str, pattern=r"^\+?[\d\s\-\(\)]{7,20}$"),
    ValidationRule("company", field_type=str, max_len=200),
]

UPDATE_RULES = [
    ValidationRule("name", field_type=str, min_len=1, max_len=200),
    ValidationRule("email", field_type=str, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_len=255),
    ValidationRule("phone", field_type=str, pattern=r"^\+?[\d\s\-\(\)]{7,20}$"),
    ValidationRule("company", field_type=str, max_len=200),
]


@client_bp.route("", methods=["GET"])
@require_permission("clients:read")
@api_response
def list_clients():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    query = {}
    if not g.roles or not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = g.user_id

    total = db.clients.count_documents(query)
    cursor = db.clients.find(query).sort("created_at", -1)
    clients = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for c in clients:
        c["_id"] = str(c["_id"])
    return paginated({"clients": clients}, page, per_page, total)


@client_bp.route("", methods=["POST"])
@require_permission("clients:write")
@api_response
def create_client():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(CREATE_RULES, data)
    if error:
        return error

    client = {
        "name": data["name"],
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "company": data.get("company", ""),
        "owner_id": g.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.clients.insert_one(client)
    client["_id"] = str(result.inserted_id)
    return created(data={"client": client}, message="Client created")


@client_bp.route("/<client_id>", methods=["GET"])
@require_permission("clients:read")
@require_ownership("clients")
@api_response
def get_client(client_id):
    db = _db.get_db()
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        return not_found(message="Client not found")
    client["_id"] = str(client["_id"])
    return success(data={"client": client})


@client_bp.route("/<client_id>", methods=["PUT"])
@require_permission("clients:write")
@require_ownership("clients")
@api_response
def update_client(client_id):
    data = request.get_json()
    if not data:
        return bad_request(message="No data provided", code="MISSING_FIELD")

    error = validate_request(UPDATE_RULES, data)
    if error:
        return error

    updates = {k: v for k, v in data.items() if k in ("name", "email", "phone", "company")}
    updates["updated_at"] = datetime.now(timezone.utc)

    db = _db.get_db()
    result = db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Client not found")

    client = db.clients.find_one({"_id": ObjectId(client_id)})
    client["_id"] = str(client["_id"])
    return success(data={"client": client}, message="Client updated")


@client_bp.route("/<client_id>", methods=["DELETE"])
@require_permission("clients:delete")
@require_ownership("clients")
@api_response
def delete_client(client_id):
    db = _db.get_db()
    result = db.clients.delete_one({"_id": ObjectId(client_id)})
    if result.deleted_count == 0:
        return not_found(message="Client not found")
    return success(message="Client deleted")
