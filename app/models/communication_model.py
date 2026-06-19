"""
Portal 5 - CRM & Client Management
Communication Model: Schema definitions and data helpers

Author: P5-A2 (CRM Backend Engineer)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CommunicationType(str, Enum):
    """Valid communication log types."""
    NOTE = "note"
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    FILE = "file"


REQUIRED_FIELDS: list[str] = [
    "type",
    "content",
]


def build_communication_document(
    data: dict[str, Any],
    created_by: str,
) -> dict[str, Any]:
    """
    Construct a new communication document for MongoDB insertion.

    Args:
        data: Validated communication payload
        created_by: User ID of the creator

    Returns:
        Complete communication document dict
    """
    # Support `communication_type` while keeping `type` key for compatibility
    comm_type = data.get("communication_type") or data.get("type")
    return {
        "client_id": data.get("client_id"),
        "lead_id": data.get("lead_id"),
        "type": comm_type,
        "communication_type": comm_type,
        "subject": data.get("subject", ""),
        "content": data["content"].strip(),
        "attendees": data.get("attendees", []),
        "action_items": data.get("action_items", []),
        "file_urls": data.get("file_urls", []),
        "created_by": created_by,
        "created_at": datetime.utcnow(),
    }


def serialize_communication(comm: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize a MongoDB communication document to a JSON-safe dict.

    Args:
        comm: Raw MongoDB document

    Returns:
        Serialized dict with string IDs and ISO datetime strings
    """
    if not comm:
        return {}

    return {
        "id": str(comm["_id"]),
        "client_id": str(comm["client_id"]) if comm.get("client_id") else None,
        "lead_id": str(comm["lead_id"]) if comm.get("lead_id") else None,
        "communication_type": comm.get("communication_type") or comm.get("type", ""),
        "type": comm.get("communication_type") or comm.get("type", ""),
        "subject": comm.get("subject", ""),
        "content": comm.get("content", ""),
        "attendees": comm.get("attendees", []),
        "action_items": comm.get("action_items", []),
        "file_urls": comm.get("file_urls", []),
        "created_by": comm.get("created_by"),
        "created_at": (
            comm["created_at"].isoformat()
            if isinstance(comm.get("created_at"), datetime)
            else None
        ),
    }
