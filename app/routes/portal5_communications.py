"""
Portal 5 - CRM & Client Management
Communications Routes: Contract endpoints for client communications

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint, g, request

from app.middleware.auth_middleware import verify_token, require_roles
from app.services.communication_service import CommunicationService
from app.services.activity_service import ActivityService
from app.utils.ownership import verify_ownership
from app.utils.response_helper import error_response, success_response

logger = logging.getLogger(__name__)

comm_bp = Blueprint("portal5_communications", __name__, url_prefix="/api/portal5")


@comm_bp.route("/clients/<client_id>/communications", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def list_client_communications(client_id: str):
    """
    GET /api/portal5/clients/:clientId/communications
    """
    comm_type = request.args.get("type")
    order = request.args.get("order", "desc")

    records, errors = CommunicationService.get_by_client(client_id, comm_type, order)
    if errors:
        return error_response(errors[0], 400)

    return success_response(records, "Communications fetched successfully.")


@comm_bp.route("/clients/<client_id>/communications", methods=["POST"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def create_client_communication(client_id: str):
    """
    POST /api/portal5/clients/:clientId/communications
    """
    # Ownership check on the parent client
    owner_ok, owner_err = verify_ownership("client", client_id, g.current_user)
    if not owner_ok:
        return error_response(owner_err or "Unauthorized", 403)

    data = request.get_json(silent=True) or {}
    # ensure client_id present and authoritative
    data["client_id"] = client_id

    comm, errors = CommunicationService.create_communication(
        data=data, created_by=g.current_user["user_id"]
    )
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    # Log activity
    try:
        ActivityService.log_activity(
            action="communication_created",
            performed_by=g.current_user["user_id"],
            details=f"Logged communication of type '{comm.get('communication_type')}' for client {client_id}",
            resource_type="client",
            resource_id=client_id,
        )
    except Exception:
        logger.exception("Failed to log communication activity")

    return success_response(comm, "Communication logged successfully.", 201)


@comm_bp.route("/communications/<comm_id>", methods=["DELETE"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def delete_communication(comm_id: str):
    """
    DELETE /api/portal5/communications/:id
    """
    # ownership check
    owner_ok, owner_err = verify_ownership("communication", comm_id, g.current_user)
    if not owner_ok:
        return error_response(owner_err or "Unauthorized", 403)

    success, error = CommunicationService.delete_communication(comm_id)
    if error:
        return error_response(error, 400)
    if not success:
        return error_response("Communication not found.", 404)

    return success_response(None, "Communication deleted successfully.")
