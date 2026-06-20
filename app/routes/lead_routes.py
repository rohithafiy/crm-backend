"""
Portal 5 - CRM & Client Management
Lead Routes: REST API endpoints for lead management

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint, g, request

from app.middleware.auth_middleware import verify_token
from app.utils.ownership import verify_ownership
from app.services.lead_service import LeadService
from app.utils.pagination_helper import get_pagination_params, get_sort_params
from app.utils.response_helper import error_response, paginated_response, success_response
from app.validators.lead_validator import (
    validate_assign_lead,
    validate_create_lead,
    validate_update_lead,
)

logger = logging.getLogger(__name__)

leads_bp = Blueprint("leads", __name__, url_prefix="/api/portal5/leads")


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("", methods=["POST"])
@verify_token
def create_lead():
    """
    Create a new lead.

    Body:
        full_name (str, required)
        email     (str, required)
        phone     (str, required)
        source    (str, required)
        company_name, industry, service_type, project_description,
        budget_range, timeline, estimated_value, portal1_request_id,
        assigned_to, follow_up_date, notes, file_urls  (all optional)

    Returns:
        201 with created lead | 400 on validation error | 409 on duplicate
    """
    data = request.get_json(silent=True) or {}
    errors = validate_create_lead(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        lead = LeadService.create_lead(data, created_by=g.current_user["user_id"])
        return success_response(lead, "Lead created successfully.", 201)
    except ValueError as exc:
        return error_response(str(exc), 409)
    except Exception as exc:
        logger.exception("Unexpected error creating lead")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  GET /api/portal5/leads
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("", methods=["GET"])
@verify_token
def list_leads():
    """
    List leads with optional filtering and pagination.

    Query params:
        page        (int, default=1)
        limit       (int, default=20, max=100)
        status      (str, optional)
        assigned_to (str, optional)
        source      (str, optional)
        search      (str, optional — searches full_name, company_name, email)

    Returns:
        200 with paginated lead list
    """
    page, limit = get_pagination_params(request)
    status = request.args.get("status")
    assigned_to = request.args.get("assigned_to")
    source = request.args.get("source")
    search = request.args.get("search")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    pipeline_stage = request.args.get("pipeline_stage")
    sort_field, sort_order = get_sort_params(request)

    try:
        leads, total = LeadService.get_leads(
            page=page,
            limit=limit,
            status=status,
            assigned_to=assigned_to,
            source=source,
            search=search,
            date_from=date_from,
            date_to=date_to,
            pipeline_stage=pipeline_stage,
            sort_field=sort_field,
            sort_order=sort_order,
        )
        return paginated_response(leads, page, limit, total, "Leads fetched successfully.")
    except Exception as exc:
        logger.exception("Unexpected error listing leads")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  GET /api/portal5/leads/<id>
            from app.middleware.auth_middleware import require_roles
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/<lead_id>", methods=["GET"])
@verify_token
def get_lead(lead_id: str):
    """
    Fetch a single lead by ID.

    Path param:
        lead_id (str): MongoDB ObjectId

    Returns:
        200 with lead | 404 if not found | 400 on invalid ID
    """
    try:
        lead = LeadService.get_lead_by_id(lead_id)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error fetching lead %s", lead_id)
        return error_response("Internal server error.", 500)

    if not lead:
        return error_response("Lead not found.", 404)

    return success_response(lead, "Lead fetched successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  PUT /api/portal5/leads/<id>
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/<lead_id>", methods=["PUT"])
@verify_token
def update_lead(lead_id: str):
    """
    Partially update a lead.

    Path param:
                # Ownership check
                owner_ok, owner_err = verify_ownership("lead", lead_id, g.current_user)
                if not owner_ok:
                    return error_response(owner_err or "Unauthorized", 403)

        lead_id (str): MongoDB ObjectId

    Body:
        Any subset of lead fields (except _id, created_at, created_by)

    Returns:
        200 with updated lead | 400 on validation | 404 if not found
    """
    data = request.get_json(silent=True) or {}
    errors = validate_update_lead(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        lead = LeadService.update_lead(lead_id, data)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error updating lead %s", lead_id)
        return error_response("Internal server error.", 500)

    if not lead:
        return error_response("Lead not found.", 404)

    return success_response(lead, "Lead updated successfully.")


# ────────────────────────────────────────────────────────────────────────────
                owner_ok, owner_err = verify_ownership("lead", lead_id, g.current_user)
                if not owner_ok:
                    return error_response(owner_err or "Unauthorized", 403)

#  DELETE /api/portal5/leads/<id>
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/<lead_id>", methods=["DELETE"])
@verify_token
def delete_lead(lead_id: str):
    """
    Soft-delete a lead (sets is_deleted=True).

    Path param:
        lead_id (str): MongoDB ObjectId

    Returns:
        200 on success | 404 if not found | 400 on invalid ID
    """
    try:
        deleted = LeadService.delete_lead(lead_id)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error deleting lead %s", lead_id)
        return error_response("Internal server error.", 500)

    if not deleted:
        return error_response("Lead not found.", 404)

    return success_response(None, "Lead deleted successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads/<id>/assign
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/<lead_id>/assign", methods=["POST"])
@verify_token
def assign_lead(lead_id: str):
    """
    Assign a lead to a user.

                owner_ok, owner_err = verify_ownership("lead", lead_id, g.current_user)
                if not owner_ok:
                    return error_response(owner_err or "Unauthorized", 403)

    Path param:
        lead_id (str): MongoDB ObjectId

    Body:
        assigned_to (str, required): Target user ID
        note        (str, optional): Assignment note

    Returns:
        200 with updated lead | 400 on validation | 404 if not found
    """
    data = request.get_json(silent=True) or {}
    errors = validate_assign_lead(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        lead = LeadService.assign_lead(
            lead_id=lead_id,
            assigned_to=data["assigned_to"],
            assigned_by=g.current_user["user_id"],
            note=data.get("note", ""),
        )
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error assigning lead %s", lead_id)
        return error_response("Internal server error.", 500)

    if not lead:
        return error_response("Lead not found.", 404)

    return success_response(lead, "Lead assigned successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads/bulk-assign
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/bulk-assign", methods=["POST"])
@verify_token
@require_roles("super_admin", "ops_lead")
def bulk_assign():
    """Bulk assign leads to a user."""
    data = request.get_json(silent=True) or {}
    lead_ids = data.get("lead_ids") or []
    assigned_to = data.get("assigned_to")
    note = data.get("note", "")
    if not lead_ids or not isinstance(lead_ids, list) or not assigned_to:
        return error_response("'lead_ids' (list) and 'assigned_to' are required.", 400)

    try:
        modified = LeadService.bulk_assign(lead_ids=lead_ids, assigned_to=assigned_to, assigned_by=g.current_user["user_id"], note=note)
        return success_response({"modified_count": modified}, "Bulk assign completed.")
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error performing bulk assign")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads/bulk-status
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/bulk-status", methods=["POST"])
@verify_token
@require_roles("super_admin", "ops_lead")
def bulk_status():
    """Bulk update status for multiple leads."""
    data = request.get_json(silent=True) or {}
    lead_ids = data.get("lead_ids") or []
    status = data.get("status")
    if not lead_ids or not isinstance(lead_ids, list) or not status:
        return error_response("'lead_ids' (list) and 'status' are required.", 400)

    try:
        modified = LeadService.bulk_status(lead_ids=lead_ids, status=status, updated_by=g.current_user["user_id"])
        return success_response({"modified_count": modified}, "Bulk status update completed.")
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error performing bulk status update")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads/bulk-delete
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/bulk-delete", methods=["POST"])
@verify_token
@require_roles("super_admin", "ops_lead")
def bulk_delete():
    """Bulk soft-delete leads."""
    data = request.get_json(silent=True) or {}
    lead_ids = data.get("lead_ids") or []
    if not lead_ids or not isinstance(lead_ids, list):
        return error_response("'lead_ids' (list) is required.", 400)

    try:
        modified = LeadService.bulk_delete(lead_ids=lead_ids, deleted_by=g.current_user["user_id"])
        return success_response({"modified_count": modified}, "Bulk delete completed.")
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error performing bulk delete")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/leads/<id>/convert
# ────────────────────────────────────────────────────────────────────────────
@leads_bp.route("/<lead_id>/convert", methods=["POST"])
                owner_ok, owner_err = verify_ownership("lead", lead_id, g.current_user)
                if not owner_ok:
                    return error_response(owner_err or "Unauthorized", 403)

@verify_token
def convert_lead(lead_id: str):
    """
    Convert a qualified lead into a client record.

    Rules:
        - Lead must exist and not be deleted
        - Lead status must be 'qualified'
        - Creates client record and sets lead status to 'won'

    Path param:
        lead_id (str): MongoDB ObjectId

    Returns:
        201 with {lead, client} | 400 on business rule violation | 404 if not found
    """
    try:
        result = LeadService.convert_lead(
            lead_id=lead_id,
            converted_by=g.current_user["user_id"],
        )
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error converting lead %s", lead_id)
        return error_response("Internal server error.", 500)

    if not result:
        return error_response("Lead not found.", 404)

    return success_response(result, "Lead converted to client successfully.", 201)
