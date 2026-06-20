from datetime import datetime, timezone
from functools import wraps
from bson.objectid import ObjectId
from flask import Blueprint, g, request

from app.utils import db as _db
from app.utils.api_response import (
    api_response,
    bad_request,
    created,
    forbidden,
    not_found,
    paginated,
    success,
)
from app.utils.permission_helper import verify_client_ownership
from app.utils.audit_helper import log_audit
from app.utils.validation import ValidationRule, validate_request

client_management_bp = Blueprint("client_management", __name__)

def require_client_ownership(resource_type, id_field="id"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, "user_id", None)
            resource_id = kwargs.get(id_field)
            if not resource_id:
                return not_found(message=f"No {id_field} provided")
            if not verify_client_ownership(user_id, resource_type, resource_id):
                return forbidden(
                    message="You do not own this resource",
                    code="FORBIDDEN",
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ─── Client Dashboard ────────────────────────────────────────────────────────

@client_management_bp.route("/dashboard", methods=["GET"])
@api_response
def client_dashboard():
    user_id = getattr(g, "user_id", None)
    db = _db.get_db()
    
    # Aggregate data belonging to the client
    projects = list(db.client_projects.find({"owner_id": user_id}))
    files = list(db.client_files.find({"owner_id": user_id}))
    messages = list(db.client_messages.find({"owner_id": user_id}))
    invoices = list(db.client_invoices.find({"owner_id": user_id}))
    payments = list(db.client_payments.find({"owner_id": user_id}))
    
    for coll in (projects, files, messages, invoices, payments):
        for item in coll:
            item["_id"] = str(item["_id"])
            
    dashboard_data = {
        "projects_count": len(projects),
        "files_count": len(files),
        "messages_count": len(messages),
        "invoices_count": len(invoices),
        "payments_count": len(payments),
        "recent_projects": projects[:5],
        "recent_invoices": invoices[:5],
    }
    
    return success(data=dashboard_data)


# ─── Client Projects ────────────────────────────────────────────────────────

CREATE_PROJECT_RULES = [
    ValidationRule("title", required=True, field_type=str, min_len=1),
    ValidationRule("description", field_type=str),
]

@client_management_bp.route("/projects", methods=["GET"])
@api_response
def list_projects():
    db = _db.get_db()
    user_id = getattr(g, "user_id", None)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    
    query = {}
    if not any(r in getattr(g, "roles", []) for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = user_id
        
    total = db.client_projects.count_documents(query)
    cursor = db.client_projects.find(query).sort("created_at", -1)
    projects = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for p in projects:
        p["_id"] = str(p["_id"])
    return paginated({"projects": projects}, page, per_page, total)

@client_management_bp.route("/projects", methods=["POST"])
@api_response
def create_project():
    data = request.get_json() or {}
    error = validate_request(CREATE_PROJECT_RULES, data)
    if error:
        return error
        
    project = {
        "title": data["title"],
        "description": data.get("description", ""),
        "owner_id": getattr(g, "user_id", None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.client_projects.insert_one(project)
    project["_id"] = str(result.inserted_id)
    
    log_audit(g.user_id, "project_create", str(result.inserted_id))
    return created(data={"project": project}, message="Project created")

@client_management_bp.route("/projects/<project_id>", methods=["GET"])
@require_client_ownership("client_projects", "project_id")
@api_response
def get_project(project_id):
    db = _db.get_db()
    p = db.client_projects.find_one({"_id": ObjectId(project_id)})
    if not p:
        return not_found(message="Project not found")
    p["_id"] = str(p["_id"])
    return success(data={"project": p})

@client_management_bp.route("/projects/<project_id>", methods=["PUT"])
@require_client_ownership("client_projects", "project_id")
@api_response
def update_project(project_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {k: v for k, v in data.items() if k in ("title", "description")}
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = db.client_projects.update_one({"_id": ObjectId(project_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Project not found")
        
    p = db.client_projects.find_one({"_id": ObjectId(project_id)})
    p["_id"] = str(p["_id"])
    log_audit(g.user_id, "project_update", project_id)
    return success(data={"project": p}, message="Project updated")

@client_management_bp.route("/projects/<project_id>", methods=["DELETE"])
@require_client_ownership("client_projects", "project_id")
@api_response
def delete_project(project_id):
    db = _db.get_db()
    result = db.client_projects.delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count == 0:
        return not_found(message="Project not found")
    log_audit(g.user_id, "project_delete", project_id)
    return success(message="Project deleted")


# ─── Client Files ───────────────────────────────────────────────────────────

CREATE_FILE_RULES = [
    ValidationRule("filename", required=True, field_type=str, min_len=1),
    ValidationRule("file_url", required=True, field_type=str),
]

@client_management_bp.route("/files", methods=["GET"])
@api_response
def list_files():
    db = _db.get_db()
    user_id = getattr(g, "user_id", None)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    
    query = {}
    if not any(r in getattr(g, "roles", []) for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = user_id
        
    total = db.client_files.count_documents(query)
    cursor = db.client_files.find(query).sort("created_at", -1)
    files = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for f in files:
        f["_id"] = str(f["_id"])
    return paginated({"files": files}, page, per_page, total)

@client_management_bp.route("/files", methods=["POST"])
@api_response
def create_file():
    data = request.get_json() or {}
    error = validate_request(CREATE_FILE_RULES, data)
    if error:
        return error
        
    file_doc = {
        "filename": data["filename"],
        "file_url": data["file_url"],
        "owner_id": getattr(g, "user_id", None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.client_files.insert_one(file_doc)
    file_doc["_id"] = str(result.inserted_id)
    log_audit(g.user_id, "file_upload", str(result.inserted_id))
    return created(data={"file": file_doc}, message="File uploaded")

@client_management_bp.route("/files/<file_id>", methods=["GET"])
@require_client_ownership("client_files", "file_id")
@api_response
def get_file(file_id):
    db = _db.get_db()
    f = db.client_files.find_one({"_id": ObjectId(file_id)})
    if not f:
        return not_found(message="File not found")
    f["_id"] = str(f["_id"])
    return success(data={"file": f})

@client_management_bp.route("/files/<file_id>", methods=["PUT"])
@require_client_ownership("client_files", "file_id")
@api_response
def update_file(file_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {k: v for k, v in data.items() if k in ("filename", "file_url")}
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = db.client_files.update_one({"_id": ObjectId(file_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="File not found")
        
    f = db.client_files.find_one({"_id": ObjectId(file_id)})
    f["_id"] = str(f["_id"])
    return success(data={"file": f}, message="File updated")

@client_management_bp.route("/files/<file_id>", methods=["DELETE"])
@require_client_ownership("client_files", "file_id")
@api_response
def delete_file(file_id):
    db = _db.get_db()
    result = db.client_files.delete_one({"_id": ObjectId(file_id)})
    if result.deleted_count == 0:
        return not_found(message="File not found")
    log_audit(g.user_id, "file_delete", file_id)
    return success(message="File deleted")


# ─── Client Messages ────────────────────────────────────────────────────────

CREATE_MESSAGE_RULES = [
    ValidationRule("content", required=True, field_type=str, min_len=1),
]

@client_management_bp.route("/messages", methods=["GET"])
@api_response
def list_messages():
    db = _db.get_db()
    user_id = getattr(g, "user_id", None)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    
    query = {}
    if not any(r in getattr(g, "roles", []) for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = user_id
        
    total = db.client_messages.count_documents(query)
    cursor = db.client_messages.find(query).sort("created_at", -1)
    messages = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for m in messages:
        m["_id"] = str(m["_id"])
    return paginated({"messages": messages}, page, per_page, total)

@client_management_bp.route("/messages", methods=["POST"])
@api_response
def create_message():
    data = request.get_json() or {}
    error = validate_request(CREATE_MESSAGE_RULES, data)
    if error:
        return error
        
    msg = {
        "content": data["content"],
        "owner_id": getattr(g, "user_id", None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.client_messages.insert_one(msg)
    msg["_id"] = str(result.inserted_id)
    return created(data={"message": msg}, message="Message sent")

@client_management_bp.route("/messages/<message_id>", methods=["GET"])
@require_client_ownership("client_messages", "message_id")
@api_response
def get_message(message_id):
    db = _db.get_db()
    m = db.client_messages.find_one({"_id": ObjectId(message_id)})
    if not m:
        return not_found(message="Message not found")
    m["_id"] = str(m["_id"])
    return success(data={"message": m})

@client_management_bp.route("/messages/<message_id>", methods=["PUT"])
@require_client_ownership("client_messages", "message_id")
@api_response
def update_message(message_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {"content": data.get("content", ""), "updated_at": datetime.now(timezone.utc)}
    
    result = db.client_messages.update_one({"_id": ObjectId(message_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Message not found")
        
    m = db.client_messages.find_one({"_id": ObjectId(message_id)})
    m["_id"] = str(m["_id"])
    return success(data={"message": m}, message="Message updated")

@client_management_bp.route("/messages/<message_id>", methods=["DELETE"])
@require_client_ownership("client_messages", "message_id")
@api_response
def delete_message(message_id):
    db = _db.get_db()
    result = db.client_messages.delete_one({"_id": ObjectId(message_id)})
    if result.deleted_count == 0:
        return not_found(message="Message not found")
    return success(message="Message deleted")


# ─── Client Invoices ────────────────────────────────────────────────────────

CREATE_INVOICE_RULES = [
    ValidationRule("amount", required=True, field_type=(int, float)),
    ValidationRule("description", field_type=str),
]

@client_management_bp.route("/invoices", methods=["GET"])
@api_response
def list_invoices():
    db = _db.get_db()
    user_id = getattr(g, "user_id", None)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    
    query = {}
    if not any(r in getattr(g, "roles", []) for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = user_id
        
    total = db.client_invoices.count_documents(query)
    cursor = db.client_invoices.find(query).sort("created_at", -1)
    invoices = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for inv in invoices:
        inv["_id"] = str(inv["_id"])
    return paginated({"invoices": invoices}, page, per_page, total)

@client_management_bp.route("/invoices", methods=["POST"])
@api_response
def create_invoice():
    data = request.get_json() or {}
    error = validate_request(CREATE_INVOICE_RULES, data)
    if error:
        return error
        
    invoice = {
        "amount": data["amount"],
        "description": data.get("description", ""),
        "status": "pending",
        "owner_id": getattr(g, "user_id", None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.client_invoices.insert_one(invoice)
    invoice["_id"] = str(result.inserted_id)
    log_audit(g.user_id, "invoice_create", str(result.inserted_id))
    return created(data={"invoice": invoice}, message="Invoice created")

@client_management_bp.route("/invoices/<invoice_id>", methods=["GET"])
@require_client_ownership("client_invoices", "invoice_id")
@api_response
def get_invoice(invoice_id):
    db = _db.get_db()
    inv = db.client_invoices.find_one({"_id": ObjectId(invoice_id)})
    if not inv:
        return not_found(message="Invoice not found")
    inv["_id"] = str(inv["_id"])
    return success(data={"invoice": inv})

@client_management_bp.route("/invoices/<invoice_id>", methods=["PUT"])
@require_client_ownership("client_invoices", "invoice_id")
@api_response
def update_invoice(invoice_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {k: v for k, v in data.items() if k in ("amount", "description", "status")}
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = db.client_invoices.update_one({"_id": ObjectId(invoice_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Invoice not found")
        
    inv = db.client_invoices.find_one({"_id": ObjectId(invoice_id)})
    inv["_id"] = str(inv["_id"])
    log_audit(g.user_id, "invoice_update", invoice_id)
    return success(data={"invoice": inv}, message="Invoice updated")

@client_management_bp.route("/invoices/<invoice_id>", methods=["DELETE"])
@require_client_ownership("client_invoices", "invoice_id")
@api_response
def delete_invoice(invoice_id):
    db = _db.get_db()
    result = db.client_invoices.delete_one({"_id": ObjectId(invoice_id)})
    if result.deleted_count == 0:
        return not_found(message="Invoice not found")
    log_audit(g.user_id, "invoice_delete", invoice_id)
    return success(message="Invoice deleted")


# ─── Client Payments ────────────────────────────────────────────────────────

CREATE_PAYMENT_RULES = [
    ValidationRule("amount", required=True, field_type=(int, float)),
    ValidationRule("invoice_id", required=True, field_type=str),
]

@client_management_bp.route("/payments", methods=["GET"])
@api_response
def list_payments():
    db = _db.get_db()
    user_id = getattr(g, "user_id", None)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    
    query = {}
    if not any(r in getattr(g, "roles", []) for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = user_id
        
    total = db.client_payments.count_documents(query)
    cursor = db.client_payments.find(query).sort("created_at", -1)
    payments = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for p in payments:
        p["_id"] = str(p["_id"])
    return paginated({"payments": payments}, page, per_page, total)

@client_management_bp.route("/payments", methods=["POST"])
@api_response
def create_payment():
    data = request.get_json() or {}
    error = validate_request(CREATE_PAYMENT_RULES, data)
    if error:
        return error
        
    payment = {
        "amount": data["amount"],
        "invoice_id": data["invoice_id"],
        "owner_id": getattr(g, "user_id", None),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.client_payments.insert_one(payment)
    payment["_id"] = str(result.inserted_id)
    
    # Also update invoice status to paid if payment is recorded
    db.client_invoices.update_one(
        {"_id": ObjectId(data["invoice_id"])},
        {"$set": {"status": "paid", "updated_at": datetime.now(timezone.utc)}}
    )
    
    log_audit(g.user_id, "payment_create", str(result.inserted_id), {"invoice_id": data["invoice_id"]})
    return created(data={"payment": payment}, message="Payment recorded")

@client_management_bp.route("/payments/<payment_id>", methods=["GET"])
@require_client_ownership("client_payments", "payment_id")
@api_response
def get_payment(payment_id):
    db = _db.get_db()
    p = db.client_payments.find_one({"_id": ObjectId(payment_id)})
    if not p:
        return not_found(message="Payment not found")
    p["_id"] = str(p["_id"])
    return success(data={"payment": p})

@client_management_bp.route("/payments/<payment_id>", methods=["PUT"])
@require_client_ownership("client_payments", "payment_id")
@api_response
def update_payment(payment_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {"amount": data.get("amount"), "updated_at": datetime.now(timezone.utc)}
    
    result = db.client_payments.update_one({"_id": ObjectId(payment_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Payment not found")
        
    p = db.client_payments.find_one({"_id": ObjectId(payment_id)})
    p["_id"] = str(p["_id"])
    log_audit(g.user_id, "payment_update", payment_id)
    return success(data={"payment": p}, message="Payment updated")

@client_management_bp.route("/payments/<payment_id>", methods=["DELETE"])
@require_client_ownership("client_payments", "payment_id")
@api_response
def delete_payment(payment_id):
    db = _db.get_db()
    result = db.client_payments.delete_one({"_id": ObjectId(payment_id)})
    if result.deleted_count == 0:
        return not_found(message="Payment not found")
    log_audit(g.user_id, "payment_delete", payment_id)
    return success(message="Payment deleted")
