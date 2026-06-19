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

invoice_bp = Blueprint("invoices", __name__)

INVOICE_STATUSES = ["pending", "sent", "paid", "overdue", "cancelled"]

CREATE_RULES = [
    ValidationRule("client_id", required=True, field_type=str),
    ValidationRule("amount", required=True, field_type=(int, float), min_value=0),
    ValidationRule("status", field_type=str, enum=INVOICE_STATUSES),
    ValidationRule("due_date", field_type=str),
    ValidationRule("description", field_type=str, max_len=5000),
]

UPDATE_RULES = [
    ValidationRule("amount", field_type=(int, float), min_value=0),
    ValidationRule("status", field_type=str, enum=INVOICE_STATUSES),
    ValidationRule("due_date", field_type=str),
    ValidationRule("description", field_type=str, max_len=5000),
]


@invoice_bp.route("", methods=["GET"])
@require_permission("invoices:read")
@api_response
def list_invoices():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    query = {}
    if not g.roles or not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = g.user_id

    total = db.invoices.count_documents(query)
    cursor = db.invoices.find(query).sort("created_at", -1)
    invoices = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for inv in invoices:
        inv["_id"] = str(inv["_id"])
    return paginated({"invoices": invoices}, page, per_page, total)


@invoice_bp.route("", methods=["POST"])
@require_permission("invoices:write")
@api_response
def create_invoice():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(CREATE_RULES, data)
    if error:
        return error

    invoice = {
        "client_id": data["client_id"],
        "amount": data["amount"],
        "status": data.get("status", "pending"),
        "due_date": data.get("due_date", ""),
        "description": data.get("description", ""),
        "owner_id": g.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.invoices.insert_one(invoice)
    invoice["_id"] = str(result.inserted_id)
    return created(data={"invoice": invoice}, message="Invoice created")


@invoice_bp.route("/<invoice_id>", methods=["GET"])
@require_permission("invoices:read")
@require_ownership("invoices")
@api_response
def get_invoice(invoice_id):
    db = _db.get_db()
    invoice = db.invoices.find_one({"_id": ObjectId(invoice_id)})
    if not invoice:
        return not_found(message="Invoice not found")
    invoice["_id"] = str(invoice["_id"])
    return success(data={"invoice": invoice})


@invoice_bp.route("/<invoice_id>", methods=["PUT"])
@require_permission("invoices:write")
@require_ownership("invoices")
@api_response
def update_invoice(invoice_id):
    data = request.get_json()
    if not data:
        return bad_request(message="No data provided", code="MISSING_FIELD")

    error = validate_request(UPDATE_RULES, data)
    if error:
        return error

    allowed = ("amount", "status", "due_date", "description")
    updates = {k: v for k, v in data.items() if k in allowed}
    updates["updated_at"] = datetime.now(timezone.utc)

    db = _db.get_db()
    result = db.invoices.update_one({"_id": ObjectId(invoice_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Invoice not found")

    invoice = db.invoices.find_one({"_id": ObjectId(invoice_id)})
    invoice["_id"] = str(invoice["_id"])
    return success(data={"invoice": invoice}, message="Invoice updated")


@invoice_bp.route("/<invoice_id>", methods=["DELETE"])
@require_permission("invoices:delete")
@require_ownership("invoices")
@api_response
def delete_invoice(invoice_id):
    db = _db.get_db()
    result = db.invoices.delete_one({"_id": ObjectId(invoice_id)})
    if result.deleted_count == 0:
        return not_found(message="Invoice not found")
    return success(message="Invoice deleted")


@invoice_bp.route("/<invoice_id>/approve", methods=["POST"])
@require_permission("invoices:approve")
@api_response
def approve_invoice(invoice_id):
    db = _db.get_db()
    result = db.invoices.update_one(
        {"_id": ObjectId(invoice_id)},
        {
            "$set": {
                "status": "paid",
                "approved_by": g.user_id,
                "approved_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        return not_found(message="Invoice not found")

    invoice = db.invoices.find_one({"_id": ObjectId(invoice_id)})
    invoice["_id"] = str(invoice["_id"])
    return success(data={"invoice": invoice}, message="Invoice approved")
