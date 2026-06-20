"""
Portal 5 - CRM & Client Management
Client Model: Schema definitions, enums, and data helpers

Author: P5-A2 (CRM Backend Engineer)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from app.utils.phone_helper import normalize_phone


class ClientStatus(str, Enum):
    """Valid client lifecycle statuses."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"


REQUIRED_FIELDS: list[str] = [
    "company_name",
    "contact_person",
    "email",
    "phone",
]

OPTIONAL_FIELDS: list[str] = [
    "company_logo_url",
    "industry",
    "address",
    "website",
    "gst_number",
    "lead_id",
    "user_id",
]


def build_client_document(
    data: dict[str, Any],
    created_by: str,
    lead_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Construct a new client document for MongoDB insertion.

    Returns:
        Complete client document dict
    """
    now = datetime.utcnow()
    client_name = (data.get("client_name") or data.get("contact_person") or "").strip()
    contact_person = data.get("contact_person", client_name).strip() if isinstance(data.get("contact_person", client_name), str) else client_name
    return {
        "user_id": data.get("user_id"),
        "company_name": data["company_name"].strip(),
        "client_name": client_name,
        "company_logo_url": data.get("company_logo_url", ""),
        "industry": data.get("industry", ""),
        "contact_person": contact_person,
        "email": data["email"].strip().lower(),
        "phone": data["phone"].strip(),
        "phone_normalized": normalize_phone(data.get("phone")),
        "address": data.get("address", ""),
        "website": data.get("website", ""),
        "gst_number": data.get("gst_number", ""),
        "lead_id": lead_id or data.get("lead_id"),
        "status": ClientStatus.ACTIVE,
        "total_revenue": 0.0,
        "total_projects": 0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
        "deleted_at": None,
    }


def serialize_client(client: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize a MongoDB client document to a JSON-safe dict.

    Args:
        client: Raw MongoDB document

    Returns:
        Serialized dict with string IDs and ISO datetime strings
    """
    if not client:
        return {}

    return {
        "id": str(client["_id"]),
        "user_id": client.get("user_id"),
        "company_name": client.get("company_name", ""),
        "client_name": client.get("client_name") or client.get("contact_person", ""),
        "company_logo_url": client.get("company_logo_url", ""),
        "industry": client.get("industry", ""),
        "contact_person": client.get("contact_person", ""),
        "email": client.get("email", ""),
        "phone": client.get("phone", ""),
        "address": client.get("address", ""),
        "website": client.get("website", ""),
        "gst_number": client.get("gst_number", ""),
        "lead_id": str(client["lead_id"]) if client.get("lead_id") else None,
        "status": client.get("status", ClientStatus.ACTIVE),
        "total_revenue": client.get("total_revenue", 0.0),
        "total_projects": client.get("total_projects", 0),
        "created_by": client.get("created_by"),
        "created_at": (
            client["created_at"].isoformat()
            if isinstance(client.get("created_at"), datetime)
            else None
        ),
        "updated_at": (
            client["updated_at"].isoformat()
            if isinstance(client.get("updated_at"), datetime)
            else None
        ),
    }
