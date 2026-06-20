"""
Ownership helper utilities for resource-level authorization checks.

Simple policy:
- `super_admin` role bypasses ownership checks
- Resource owner (`created_by`) or current assignee (`assigned_to`) are considered owners

This is intentionally lightweight and intended for enforcement in route handlers.
"""

from typing import Tuple
from bson import ObjectId
from bson.errors import InvalidId

from app.database.db import get_leads_collection, get_clients_collection, get_communications_collection


def _get_collection_for(resource_type: str):
    if resource_type == "lead":
        return get_leads_collection()
    if resource_type == "client":
        return get_clients_collection()
    if resource_type == "communication":
        return get_communications_collection()
    return None


def verify_ownership(resource_type: str, resource_id: str, current_user: dict) -> Tuple[bool, str]:
    """Return (True, '') if the current_user is allowed to mutate the resource.

    Otherwise returns (False, message).
    """
    # super_admin bypass
    if not current_user:
        return False, "Authentication required"
    role = current_user.get("role", "")
    if role == "super_admin":
        return True, ""

    coll = _get_collection_for(resource_type)
    if coll is None:
        return False, "Unknown resource type"

    try:
        oid = ObjectId(resource_id)
    except InvalidId:
        return False, "Invalid resource id"

    doc = coll.find_one({"_id": oid})
    if not doc:
        return False, "Resource not found"

    user_id = current_user.get("user_id")
    # match created_by
    if doc.get("created_by") == user_id:
        return True, ""

    # match assigned_to (may be ObjectId)
    assigned = doc.get("assigned_to")
    if assigned and str(assigned) == str(user_id):
        return True, ""

    return False, "Insufficient permissions for this resource"
