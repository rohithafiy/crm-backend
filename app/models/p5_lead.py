"""
Portal 5 - CRM & Client Management
Lead Model: Schema definitions, enums, and data helpers

Author: P5-A2 (CRM Backend Engineer)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from bson import ObjectId
from app.utils.phone_helper import normalize_phone


class LeadStatus(str, Enum):
    """Valid lead pipeline statuses."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class LeadSource(str, Enum):
    """Lead acquisition sources as per Portal 5 spec."""
    WEBSITE = "website"
    REFERRAL = "referral"
    DIRECT = "direct"
    SOCIAL_MEDIA = "social_media"
    EVENT = "event"



# Valid pipeline stage transitions
# Key: current status → Value: allowed next statuses
VALID_TRANSITIONS: dict[str, list[str]] = {
    LeadStatus.NEW: [LeadStatus.CONTACTED, LeadStatus.LOST],
    LeadStatus.CONTACTED: [LeadStatus.QUALIFIED, LeadStatus.LOST],
    LeadStatus.QUALIFIED: [LeadStatus.PROPOSAL_SENT, LeadStatus.LOST],
    LeadStatus.PROPOSAL_SENT: [LeadStatus.NEGOTIATION, LeadStatus.LOST],
    LeadStatus.NEGOTIATION: [LeadStatus.WON, LeadStatus.LOST],
    LeadStatus.WON: [],       # Terminal state
    LeadStatus.LOST: [],      # Terminal state
}

REQUIRED_FIELDS: list[str] = [
    "full_name",
    "email",
    "service_type",
]

OPTIONAL_FIELDS: list[str] = [
    "company_name",
    "industry",
    "phone",
    "source",
    "project_description",
    "budget_range",
    "timeline",
    "estimated_value",
    "portal1_request_id",
    "assigned_to",
    "follow_up_date",
    "notes",
    "file_urls",
]


def build_lead_document(data: dict[str, Any], created_by: str) -> dict[str, Any]:
    """
    Construct a new lead document for MongoDB insertion.

    Args:
        data: Validated lead payload
        created_by: User ID of the creator

    Returns:
        Complete lead document dict
    """
    now = datetime.now(timezone.utc)
    name = data.get("full_name") or data.get("lead_name", "").strip()

    return {
        "full_name": name,
        "company_name": data.get("company_name", "").strip(),
        "email": data["email"].strip().lower(),
        "phone": data.get("phone", "").strip(),
        "phone_normalized": normalize_phone(data.get("phone")),
        "industry": data.get("industry", ""),
        "service_type": data["service_type"].strip(),
        "project_description": data.get("project_description", ""),
        "budget_range": data.get("budget_range", ""),
        "timeline": data.get("timeline", ""),
        "estimated_value": float(data["estimated_value"]) if data.get("estimated_value") else None,
        "source": data.get("source"),
        "portal1_request_id": data.get("portal1_request_id"),
        "status": LeadStatus.NEW,
        "assigned_to": data.get("assigned_to"),
        "follow_up_date": data.get("follow_up_date"),
        "notes": data.get("notes", ""),
        "file_urls": data.get("file_urls", []),
        "assignment_history": [],
        "audit_logs": [],
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
        "deleted_at": None,
    }


def serialize_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize a MongoDB lead document to a JSON-safe dict.

    Args:
        lead: Raw MongoDB document

    Returns:
        Serialized dict with string IDs and ISO datetime strings
    """
    if not lead:
        return {}

    return {
        "id": str(lead["_id"]),
        "full_name": lead.get("full_name", ""),
        "company_name": lead.get("company_name", ""),
        "email": lead.get("email", ""),
        "phone": lead.get("phone", ""),
        "industry": lead.get("industry", ""),
        "service_type": lead.get("service_type", ""),
        "project_description": lead.get("project_description", ""),
        "budget_range": lead.get("budget_range", ""),
        "timeline": lead.get("timeline", ""),
        "estimated_value": lead.get("estimated_value"),
        "source": lead.get("source", ""),
        "portal1_request_id": lead.get("portal1_request_id"),
        "status": lead.get("status", ""),
        "assigned_to": lead.get("assigned_to"),
        "follow_up_date": (
            lead["follow_up_date"].isoformat()
            if isinstance(lead.get("follow_up_date"), datetime)
            else lead.get("follow_up_date")
        ),
        "notes": lead.get("notes", ""),
        "file_urls": lead.get("file_urls", []),
        "assignment_history": [
            _serialize_assignment(a) for a in lead.get("assignment_history", [])
        ],
        "audit_logs": [_serialize_audit(a) for a in lead.get("audit_logs", [])],
        "created_by": lead.get("created_by"),
        "created_at": lead["created_at"].isoformat() if isinstance(lead.get("created_at"), datetime) else None,
        "updated_at": lead["updated_at"].isoformat() if isinstance(lead.get("updated_at"), datetime) else None,
    }


def _serialize_assignment(assignment: dict[str, Any]) -> dict[str, Any]:
    """Serialize an assignment history entry."""
    return {
        "assigned_to": str(assignment.get("assigned_to")) if assignment.get("assigned_to") is not None else None,
        "assigned_by": str(assignment.get("assigned_by")) if assignment.get("assigned_by") is not None else None,
        "note": assignment.get("note", ""),
        "assigned_at": (
            assignment["assigned_at"].isoformat()
            if isinstance(assignment.get("assigned_at"), datetime)
            else assignment.get("assigned_at")
        ),
    }


def _serialize_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Serialize an audit log entry."""
    return {
        "action": audit.get("action"),
        "performed_by": audit.get("performed_by"),
        "details": audit.get("details", ""),
        "timestamp": (
            audit["timestamp"].isoformat()
            if isinstance(audit.get("timestamp"), datetime)
            else audit.get("timestamp")
        ),
    }
