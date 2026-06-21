"""
Portal 5 - CRM & Client Management
Pipeline Routes: Pipeline board and communication history endpoints

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint, g, request

from app.middleware.auth_middleware import verify_token, require_roles
from app.services.communication_service import CommunicationService
from app.services.pipeline_service import PipelineService
from app.utils.ownership import verify_ownership
from app.utils.response_helper import error_response, success_response
from app.validators.pipeline_validator import validate_pipeline_update

logger = logging.getLogger(__name__)

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/portal5/pipeline")
comms_bp = Blueprint("communications", __name__, url_prefix="/api/portal5/communications")


# ────────────────────────────────────────────────────────────────────────────
#  PUT /api/portal5/pipeline/<lead_id>
# ────────────────────────────────────────────────────────────────────────────
@pipeline_bp.route("/<lead_id>", methods=["PUT"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def update_pipeline_stage(lead_id: str):
    """
    Move a lead to a new pipeline stage.

    Allowed transitions::

        new → contacted | lost
        contacted → qualified | lost
        qualified → proposal_sent | lost
        proposal_sent → negotiation | lost
        negotiation → won | lost

    Path param:
        lead_id (str): MongoDB ObjectId

    Body:
        status (str, required): Target stage

    Returns:
        200 with updated lead | 400 on invalid transition | 404 if not found
    """
    data = request.get_json(silent=True) or {}
    errors = validate_pipeline_update(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        lead = PipelineService.update_stage(
            lead_id=lead_id,
            new_status=data["status"],
            updated_by=g.current_user["user_id"],
        )
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error updating pipeline stage for %s", lead_id)
        return error_response("Internal server error.", 500)

    if not lead:
        return error_response("Lead not found.", 404)

    return success_response(lead, f"Lead moved to '{data['status']}' successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  GET /api/portal5/pipeline
# ────────────────────────────────────────────────────────────────────────────
@pipeline_bp.route("", methods=["GET"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def get_pipeline_board():
    """
    Get the full pipeline board grouped by stage.

    Returns:
        200 with::

            {
              "new": [...],
              "contacted": [...],
              "qualified": [...],
              "proposal_sent": [...],
              "negotiation": [...],
              "won": [...],
              "lost": [...]
            }
    """
    try:
        board = PipelineService.get_pipeline_board()
        return success_response(board, "Pipeline board fetched successfully.")
    except Exception:
        logger.exception("Unexpected error fetching pipeline board")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/communications
# ────────────────────────────────────────────────────────────────────────────
@comms_bp.route("", methods=["POST"])
@verify_token
@require_roles("super_admin", "ops_lead", "project_manager")
def create_communication():
    """
    Log a new communication entry.

    Body:
        type       (str, required): note | email | meeting | file
        content    (str, required)
        client_id  (str, optional — one of client_id or lead_id required)
        lead_id    (str, optional)
        subject    (str, optional)
        attendees  (list, optional)
        action_items (list, optional)
        file_urls  (list, optional)

    Returns:
        201 with created entry | 400 on validation error
    """
    data = request.get_json(silent=True) or {}

    # Ownership check on parent resource (client or lead)
    if data.get("client_id"):
        owner_ok, owner_err = verify_ownership("client", data["client_id"], g.current_user)
        if not owner_ok:
            return error_response(owner_err or "Unauthorized", 403)
    elif data.get("lead_id"):
        owner_ok, owner_err = verify_ownership("lead", data["lead_id"], g.current_user)
        if not owner_ok:
            return error_response(owner_err or "Unauthorized", 403)

    comm, errors = CommunicationService.create_communication(
        data=data,
        created_by=g.current_user["user_id"],
    )
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    return success_response(comm, "Communication logged successfully.", 201)

