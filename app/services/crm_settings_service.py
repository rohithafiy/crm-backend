from datetime import datetime, timezone

from bson.objectid import ObjectId
from flask import Blueprint, g, request

from app.utils import db as _db
from app.utils.api_response import (
    api_response,
    created,
    not_found,
    paginated,
    success,
)
from app.utils.audit_helper import log_audit
from app.utils.permission_helper import require_roles
from app.utils.validation import ValidationRule, validate_request

crm_settings_bp = Blueprint("crm_settings", __name__)


# ─── Email Templates ────────────────────────────────────────────────────────

EMAIL_TEMPLATE_RULES = [
    ValidationRule("name", required=True, field_type=str, min_len=1),
    ValidationRule("subject", required=True, field_type=str, min_len=1),
    ValidationRule("body", required=True, field_type=str, min_len=1),
]

@crm_settings_bp.route("/email-templates", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def list_email_templates():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    total = db.email_templates.count_documents({})
    cursor = db.email_templates.find({}).sort("created_at", -1)
    templates = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for t in templates:
        t["_id"] = str(t["_id"])
    return paginated({"email_templates": templates}, page, per_page, total)

@crm_settings_bp.route("/email-templates", methods=["POST"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def create_email_template():
    data = request.get_json() or {}
    error = validate_request(EMAIL_TEMPLATE_RULES, data)
    if error:
        return error

    template = {
        "name": data["name"],
        "subject": data["subject"],
        "body": data["body"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.email_templates.insert_one(template)
    template["_id"] = str(result.inserted_id)

    log_audit(g.user_id, "email_template_create", str(result.inserted_id))
    return created(data={"email_template": template}, message="Email template created")

@crm_settings_bp.route("/email-templates/<template_id>", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def get_email_template(template_id):
    db = _db.get_db()
    t = db.email_templates.find_one({"_id": ObjectId(template_id)})
    if not t:
        return not_found(message="Email template not found")
    t["_id"] = str(t["_id"])
    return success(data={"email_template": t})

@crm_settings_bp.route("/email-templates/<template_id>", methods=["PUT"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def update_email_template(template_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {k: v for k, v in data.items() if k in ("name", "subject", "body")}
    updates["updated_at"] = datetime.now(timezone.utc)

    result = db.email_templates.update_one({"_id": ObjectId(template_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Email template not found")

    t = db.email_templates.find_one({"_id": ObjectId(template_id)})
    t["_id"] = str(t["_id"])
    log_audit(g.user_id, "email_template_update", template_id)
    return success(data={"email_template": t}, message="Email template updated")

@crm_settings_bp.route("/email-templates/<template_id>", methods=["DELETE"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def delete_email_template(template_id):
    db = _db.get_db()
    result = db.email_templates.delete_one({"_id": ObjectId(template_id)})
    if result.deleted_count == 0:
        return not_found(message="Email template not found")
    log_audit(g.user_id, "email_template_delete", template_id)
    return success(message="Email template deleted")


# ─── Proposal Templates ─────────────────────────────────────────────────────

PROPOSAL_TEMPLATE_RULES = [
    ValidationRule("title", required=True, field_type=str, min_len=1),
    ValidationRule("content", required=True, field_type=str, min_len=1),
]

@crm_settings_bp.route("/proposal-templates", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def list_proposal_templates():
    db = _db.get_db()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    total = db.proposal_templates.count_documents({})
    cursor = db.proposal_templates.find({}).sort("created_at", -1)
    templates = list(cursor.skip((page - 1) * per_page).limit(per_page))
    for t in templates:
        t["_id"] = str(t["_id"])
    return paginated({"proposal_templates": templates}, page, per_page, total)

@crm_settings_bp.route("/proposal-templates", methods=["POST"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def create_proposal_template():
    data = request.get_json() or {}
    error = validate_request(PROPOSAL_TEMPLATE_RULES, data)
    if error:
        return error

    template = {
        "title": data["title"],
        "content": data["content"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    db = _db.get_db()
    result = db.proposal_templates.insert_one(template)
    template["_id"] = str(result.inserted_id)

    log_audit(g.user_id, "proposal_template_create", str(result.inserted_id))
    return created(data={"proposal_template": template}, message="Proposal template created")

@crm_settings_bp.route("/proposal-templates/<template_id>", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def get_proposal_template(template_id):
    db = _db.get_db()
    t = db.proposal_templates.find_one({"_id": ObjectId(template_id)})
    if not t:
        return not_found(message="Proposal template not found")
    t["_id"] = str(t["_id"])
    return success(data={"proposal_template": t})

@crm_settings_bp.route("/proposal-templates/<template_id>", methods=["PUT"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def update_proposal_template(template_id):
    data = request.get_json() or {}
    db = _db.get_db()
    updates = {k: v for k, v in data.items() if k in ("title", "content")}
    updates["updated_at"] = datetime.now(timezone.utc)

    result = db.proposal_templates.update_one({"_id": ObjectId(template_id)}, {"$set": updates})
    if result.matched_count == 0:
        return not_found(message="Proposal template not found")

    t = db.proposal_templates.find_one({"_id": ObjectId(template_id)})
    t["_id"] = str(t["_id"])
    log_audit(g.user_id, "proposal_template_update", template_id)
    return success(data={"proposal_template": t}, message="Proposal template updated")

@crm_settings_bp.route("/proposal-templates/<template_id>", methods=["DELETE"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def delete_proposal_template(template_id):
    db = _db.get_db()
    result = db.proposal_templates.delete_one({"_id": ObjectId(template_id)})
    if result.deleted_count == 0:
        return not_found(message="Proposal template not found")
    log_audit(g.user_id, "proposal_template_delete", template_id)
    return success(message="Proposal template deleted")


# ─── Tax Settings ──────────────────────────────────────────────────────────

TAX_SETTINGS_RULES = [
    ValidationRule("default_tax_rate", required=True, field_type=(int, float)),
    ValidationRule("tax_id", required=True, field_type=str),
]

@crm_settings_bp.route("/tax-settings", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def get_tax_settings():
    db = _db.get_db()
    settings = db.tax_settings.find_one({})
    if not settings:
        # Default initialization
        settings = {
            "default_tax_rate": 18.0,
            "tax_id": "GSTIN-DUMMY",
            "updated_at": datetime.now(timezone.utc)
        }
        db.tax_settings.insert_one(settings)
    settings["_id"] = str(settings["_id"])
    return success(data={"tax_settings": settings})

@crm_settings_bp.route("/tax-settings", methods=["PUT"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def update_tax_settings():
    data = request.get_json() or {}
    error = validate_request(TAX_SETTINGS_RULES, data)
    if error:
        return error

    updates = {
        "default_tax_rate": data["default_tax_rate"],
        "tax_id": data["tax_id"],
        "updated_at": datetime.now(timezone.utc)
    }
    db = _db.get_db()
    db.tax_settings.update_many({}, {"$set": updates}, upsert=True)

    settings = db.tax_settings.find_one({})
    settings["_id"] = str(settings["_id"])
    log_audit(g.user_id, "tax_settings_update", settings["_id"])
    return success(data={"tax_settings": settings}, message="Tax settings updated")


# ─── Permission Settings ────────────────────────────────────────────────────

PERMISSION_SETTINGS_RULES = [
    ValidationRule("roles_permissions", required=True, field_type=dict),
]

@crm_settings_bp.route("/permission-settings", methods=["GET"])
@require_roles(["super_admin"])
@api_response
def get_permission_settings():
    db = _db.get_db()
    settings = db.permission_settings.find_one({})
    if not settings:
        # Fetch current defaults from SecurityConfig to initialize
        from app.configs.security_config import SecurityConfig
        settings = {
            "roles_permissions": SecurityConfig.PERMISSIONS,
            "updated_at": datetime.now(timezone.utc)
        }
        db.permission_settings.insert_one(settings)
    settings["_id"] = str(settings["_id"])
    return success(data={"permission_settings": settings})

@crm_settings_bp.route("/permission-settings", methods=["PUT"])
@require_roles(["super_admin"])
@api_response
def update_permission_settings():
    data = request.get_json() or {}
    error = validate_request(PERMISSION_SETTINGS_RULES, data)
    if error:
        return error

    updates = {
        "roles_permissions": data["roles_permissions"],
        "updated_at": datetime.now(timezone.utc)
    }
    db = _db.get_db()
    db.permission_settings.update_many({}, {"$set": updates}, upsert=True)

    settings = db.permission_settings.find_one({})
    settings["_id"] = str(settings["_id"])

    log_audit(g.user_id, "permission_settings_update", settings["_id"])
    return success(data={"permission_settings": settings}, message="Permission settings updated")


# ─── General CRM Settings ───────────────────────────────────────────────────

CRM_SETTINGS_RULES = [
    ValidationRule("company_name", required=True, field_type=str, min_len=1),
    ValidationRule("support_email", required=True, field_type=str),
]

@crm_settings_bp.route("", methods=["GET"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def get_crm_settings():
    db = _db.get_db()
    settings = db.crm_settings.find_one({})
    if not settings:
        settings = {
            "company_name": "LTI Hub",
            "support_email": "support@ltihub.com",
            "updated_at": datetime.now(timezone.utc)
        }
        db.crm_settings.insert_one(settings)
    settings["_id"] = str(settings["_id"])
    return success(data={"crm_settings": settings})

@crm_settings_bp.route("", methods=["PUT"])
@require_roles(["super_admin", "ops_lead"])
@api_response
def update_crm_settings():
    data = request.get_json() or {}
    error = validate_request(CRM_SETTINGS_RULES, data)
    if error:
        return error

    updates = {
        "company_name": data["company_name"],
        "support_email": data["support_email"],
        "updated_at": datetime.now(timezone.utc)
    }
    db = _db.get_db()
    db.crm_settings.update_many({}, {"$set": updates}, upsert=True)

    settings = db.crm_settings.find_one({})
    settings["_id"] = str(settings["_id"])
    log_audit(g.user_id, "crm_settings_update", settings["_id"])
    return success(data={"crm_settings": settings}, message="CRM settings updated")
