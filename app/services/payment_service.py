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

payment_bp = Blueprint("payments", __name__)

PAYMENT_METHODS = ["bank_transfer", "credit_card", "cash", "cheque", "online"]
PAYMENT_STATUSES = ["pending", "completed", "failed", "refunded"]

CREATE_RULES = [
    ValidationRule("client_id", required=True, field_type=str),
    ValidationRule("amount", required=True, field_type=(int, float), min_value=0),
    ValidationRule("invoice_id", field_type=str),
    ValidationRule("method", field_type=str, enum=PAYMENT_METHODS),
    ValidationRule("status", field_type=str, enum=PAYMENT_STATUSES),
    ValidationRule("notes", field_type=str, max_len=2000),
]

UPDATE_RULES = [
    ValidationRule("amount", field_type=(int, float), min_value=0),
    ValidationRule("method", field_type=str, enum=PAYMENT_METHODS),
    ValidationRule("status", field_type=str, enum=PAYMENT_STATUSES),
    ValidationRule("notes", field_type=str, max_len=2000),
]


@payment_bp.route("", methods=["GET"])
@require_permission("payments:read")
@api_response
def list_payments():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    query = {}
    if not g.roles or not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["recorded_by"] = g.user_id

    total = db.payments.count_documents(query)
    cursor = db.payments.find(query).sort("created_at", -1)
    payments = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for p in payments:
        p["_id"] = str(p["_id"])
    return paginated({"payments": payments}, page, per_page, total)


@payment_bp.route("", methods=["POST"])
@require_permission("payments:write")
@api_response
def record_payment():
    data = request.get_json()
    if not data:
        return bad_request(message="Request body is required", code="MISSING_FIELD")

    error = validate_request(CREATE_RULES, data)
    if error:
        return error

    payment = {
        "client_id": data["client_id"],
        "invoice_id": data.get("invoice_id", ""),
        "amount": data["amount"],
        "method": data.get("method", "bank_transfer"),
        "status": data.get("status", "completed"),
        "notes": data.get("notes", ""),
        "recorded_by": g.user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.payments.insert_one(payment)
    payment["_id"] = str(result.inserted_id)
    return created(data={"payment": payment}, message="Payment recorded")


@payment_bp.route("/<payment_id>", methods=["GET"])
@require_permission("payments:read")
@require_ownership("payments", owner_field="recorded_by")
@api_response
def get_payment(payment_id):
    db = _db.get_db()
    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        return not_found(message="Payment not found")
    payment["_id"] = str(payment["_id"])
    return success(data={"payment": payment})


@payment_bp.route("/<payment_id>", methods=["PUT"])
@require_permission("payments:write")
@require_ownership("payments", owner_field="recorded_by")
@api_response
def update_payment(payment_id):
    data = request.get_json()
    if not data:
        return bad_request(message="No data provided", code="MISSING_FIELD")

    error = validate_request(UPDATE_RULES, data)
    if error:
        return error

    updates = {k: v for k, v in data.items() if k in ("amount", "method", "status", "notes")}
    updates["updated_at"] = datetime.now(timezone.utc)

    db = _db.get_db()
    result = db.payments.update_one({"_id": ObjectId(payment_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Payment not found")

    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    payment["_id"] = str(payment["_id"])
    return success(data={"payment": payment}, message="Payment updated")


@payment_bp.route("/<payment_id>", methods=["DELETE"])
@require_permission("payments:delete")
@require_ownership("payments", owner_field="recorded_by")
@api_response
def delete_payment(payment_id):
    db = _db.get_db()
    result = db.payments.delete_one({"_id": ObjectId(payment_id)})
    if result.deleted_count == 0:
        return not_found(message="Payment not found")
    return success(message="Payment deleted")


@payment_bp.route("/<payment_id>/refund", methods=["POST"])
@require_permission("payments:refund")
@api_response
def refund_payment(payment_id):
    db = _db.get_db()
    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        return not_found(message="Payment not found")

    result = db.payments.update_one(
        {"_id": ObjectId(payment_id)},
        {
            "$set": {
                "status": "refunded",
                "refunded_by": g.user_id,
                "refunded_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        return not_found(message="Payment not found")

    payment = db.payments.find_one({"_id": ObjectId(payment_id)})
    payment["_id"] = str(payment["_id"])
    return success(data={"payment": payment}, message="Payment refunded")
