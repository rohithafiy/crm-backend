"""
Portal 5 - CRM & Client Management
Client Routes: REST API endpoints for client management

Author: P5-A2 (CRM Backend Engineer)
"""

import logging

from flask import Blueprint, g, request

from app.middleware.auth_middleware import verify_token
from app.utils.ownership import verify_ownership
from app.services.client_service import ClientService
from app.utils.pagination_helper import get_pagination_params, get_sort_params
from app.utils.response_helper import error_response, paginated_response, success_response
from app.validators.client_validator import validate_create_client, validate_update_client

logger = logging.getLogger(__name__)

clients_bp = Blueprint("clients", __name__, url_prefix="/api/portal5/clients")


# ────────────────────────────────────────────────────────────────────────────
#  POST /api/portal5/clients
# ────────────────────────────────────────────────────────────────────────────
@clients_bp.route("", methods=["POST"])
@verify_token
def create_client():
    """
    Create a new client manually (not via lead conversion).

    Body:
        company_name   (str, required)
        contact_person (str, required)
        email          (str, required)
        phone          (str, required)
        company_logo_url, industry, address, website,
        gst_number, lead_id, user_id  (all optional)

    Returns:
        201 with created client | 400 on validation | 409 on duplicate
    """
    data = request.get_json(silent=True) or {}
    errors = validate_create_client(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        client = ClientService.create_client(
            data=data,
            created_by=g.current_user["user_id"],
        )
        return success_response(client, "Client created successfully.", 201)
    except ValueError as exc:
        return error_response(str(exc), 409)
    except Exception:
        logger.exception("Unexpected error creating client")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  GET /api/portal5/clients
# ────────────────────────────────────────────────────────────────────────────
@clients_bp.route("", methods=["GET"])
@verify_token
def list_clients():
    """
    List clients with optional filtering and pagination.

    Query params:
        page     (int, default=1)
        limit    (int, default=20, max=100)
        status   (str, optional): active | inactive | churned
        industry (str, optional)
        search   (str, optional — searches company_name, contact_person, email)

    Returns:
        200 with paginated client list
    """
    page, limit = get_pagination_params(request)
    status = request.args.get("status")
    industry = request.args.get("industry")
    search = request.args.get("search")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    assigned_user = request.args.get("assigned_user")
    sort_field, sort_order = get_sort_params(request)

    try:
        clients, total = ClientService.get_clients(
            page=page,
            limit=limit,
            status=status,
            industry=industry,
            search=search,
            date_from=date_from,
            date_to=date_to,
            assigned_user=assigned_user,
            sort_field=sort_field,
            sort_order=sort_order,
        )
        return paginated_response(clients, page, limit, total, "Clients fetched successfully.")
    except Exception:
        logger.exception("Unexpected error listing clients")
        return error_response("Internal server error.", 500)


# ────────────────────────────────────────────────────────────────────────────
#  GET /api/portal5/clients/<id>
# ────────────────────────────────────────────────────────────────────────────
@clients_bp.route("/<client_id>", methods=["GET"])
@verify_token
def get_client(client_id: str):
    """
    Fetch a single client by ID.

    Path param:
        client_id (str): MongoDB ObjectId

    Returns:
        200 with client | 404 if not found | 400 on invalid ID
    """
    try:
        client = ClientService.get_client_by_id(client_id)
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error fetching client %s", client_id)
        return error_response("Internal server error.", 500)

    if not client:
        return error_response("Client not found.", 404)

    return success_response(client, "Client fetched successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  PUT /api/portal5/clients/<id>
# ────────────────────────────────────────────────────────────────────────────
@clients_bp.route("/<client_id>", methods=["PUT"])
@verify_token
def update_client(client_id: str):
    """
    Partially update a client.

    Path param:
        client_id (str): MongoDB ObjectId

    Body:
        Any subset of client fields

    Returns:
        200 with updated client | 400 on validation | 404 if not found
    """
    data = request.get_json(silent=True) or {}
    errors = validate_update_client(data)
    if errors:
        return error_response("Validation failed.", 400, errors=errors)

    try:
        # Ownership check
        owner_ok, owner_err = verify_ownership("client", client_id, g.current_user)
        if not owner_ok:
            return error_response(owner_err or "Unauthorized", 403)

        client = ClientService.update_client(client_id, data, updated_by=g.current_user.get("user_id", "system"))
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error updating client %s", client_id)
        return error_response("Internal server error.", 500)

    if not client:
        return error_response("Client not found.", 404)

    return success_response(client, "Client updated successfully.")


# ────────────────────────────────────────────────────────────────────────────
#  DELETE /api/portal5/clients/<id>
# ────────────────────────────────────────────────────────────────────────────
@clients_bp.route("/<client_id>", methods=["DELETE"])
@verify_token
def delete_client(client_id: str):
    """
    Soft-delete a client.

    Path param:
        client_id (str): MongoDB ObjectId

    Returns:
        200 on success | 404 if not found | 400 on invalid ID
    """
    try:
        owner_ok, owner_err = verify_ownership("client", client_id, g.current_user)
        if not owner_ok:
            return error_response(owner_err or "Unauthorized", 403)

        deleted = ClientService.delete_client(client_id, deleted_by=g.current_user.get("user_id", "system"))
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception:
        logger.exception("Unexpected error deleting client %s", client_id)
        return error_response("Internal server error.", 500)

    if not deleted:
        return error_response("Client not found.", 404)

    return success_response(None, "Client deleted successfully.")
