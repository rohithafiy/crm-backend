"""
Portal 5 - CRM & Client Management
Lead Validator: Input validation for lead create/update payloads

Author: P5-A2 (CRM Backend Engineer)
"""

import re
from typing import Any

from app.models.p5_lead import LeadSource, LeadStatus, REQUIRED_FIELDS

# RFC 5322 simplified email regex
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
# E.164-compatible phone: optional +, 7-15 digits (with optional spaces/dashes)
_PHONE_RE = re.compile(r"^\+?[\d\s\-]{7,15}$")

VALID_STATUSES = {s.value for s in LeadStatus}
VALID_SOURCES = {s.value for s in LeadSource}


def validate_create_lead(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for POST /leads.

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    # Required field presence
    for field in REQUIRED_FIELDS:
        if not data.get(field, "").strip():
            errors.append(f"'{field}' is required and cannot be empty.")

    if errors:
        return errors  # Bail early; remaining checks need these fields

    # Email format
    email = data.get("email", "").strip()
    if not _EMAIL_RE.match(email):
        errors.append(f"'{email}' is not a valid email address.")

    # Phone format (optional)
    phone = data.get("phone", "").strip()
    if phone and not _PHONE_RE.match(phone):
        errors.append(f"'{phone}' is not a valid phone number.")

    # Source enum
    source = data.get("source", "")
    if source and source not in VALID_SOURCES:
        errors.append(
            f"Invalid source '{source}'. Allowed: {sorted(VALID_SOURCES)}."
        )

    # Estimated value must be numeric if provided
    ev = data.get("estimated_value")
    if ev is not None:
        try:
            float(ev)
        except (ValueError, TypeError):
            errors.append("'estimated_value' must be a numeric value.")

    # file_urls must be a list of strings
    file_urls = data.get("file_urls")
    if file_urls is not None:
        if not isinstance(file_urls, list):
            errors.append("'file_urls' must be an array.")
        elif not all(isinstance(u, str) for u in file_urls):
            errors.append("Each item in 'file_urls' must be a string URL.")

    return errors


def validate_update_lead(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for PUT /leads/<id> (partial update).

    Args:
        data: Request JSON payload (only provided fields are validated)

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    if not data:
        errors.append("Request body cannot be empty.")
        return errors

    # Email — only if being updated
    if "email" in data:
        email = data.get("email", "").strip()
        if not email:
            errors.append("'email' cannot be set to an empty value.")
        elif not _EMAIL_RE.match(email):
            errors.append(f"'{email}' is not a valid email address.")

    # Phone — only if being updated
    if "phone" in data:
        phone = data.get("phone", "").strip()
        if not phone:
            errors.append("'phone' cannot be set to an empty value.")
        elif not _PHONE_RE.match(phone):
            errors.append(f"'{phone}' is not a valid phone number.")

    # Status — only valid enums allowed
    if "status" in data:
        status = data.get("status", "")
        if status not in VALID_STATUSES:
            errors.append(
                f"Invalid status '{status}'. Allowed: {sorted(VALID_STATUSES)}."
            )

    # Source
    if "source" in data:
        source = data.get("source", "")
        if source and source not in VALID_SOURCES:
            errors.append(
                f"Invalid source '{source}'. Allowed: {sorted(VALID_SOURCES)}."
            )

    # Estimated value
    if "estimated_value" in data:
        ev = data.get("estimated_value")
        if ev is not None:
            try:
                float(ev)
            except (ValueError, TypeError):
                errors.append("'estimated_value' must be a numeric value.")

    return errors


def validate_assign_lead(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for POST /leads/<id>/assign.

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    assigned_to = data.get("assigned_to", "").strip()
    if not assigned_to:
        errors.append("'assigned_to' (user_id) is required.")

    return errors
