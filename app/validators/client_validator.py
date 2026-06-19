"""
Portal 5 - CRM & Client Management
Client Validator: Input validation for client create/update payloads

Author: P5-A2 (CRM Backend Engineer)
"""

import re
from typing import Any

from app.models.client_model import ClientStatus, REQUIRED_FIELDS

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-]{7,15}$")
_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
# Indian GST format: 2-digit state + 10-digit PAN + 1 + Z + 1 checksum
_GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$")

VALID_STATUSES = {s.value for s in ClientStatus}


def validate_create_client(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for POST /clients.

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if not data.get(field, "").strip():
            errors.append(f"'{field}' is required and cannot be empty.")

    if errors:
        return errors

    # Email
    email = data.get("email", "").strip()
    if not _EMAIL_RE.match(email):
        errors.append(f"'{email}' is not a valid email address.")

    # Phone
    phone = data.get("phone", "").strip()
    if not _PHONE_RE.match(phone):
        errors.append(f"'{phone}' is not a valid phone number.")

    # Website URL (optional)
    website = data.get("website", "").strip()
    if website and not _URL_RE.match(website):
        errors.append(f"'{website}' is not a valid website URL.")

    # GST number (optional but validated if present)
    gst = data.get("gst_number", "").strip()
    if gst and not _GST_RE.match(gst):
        errors.append(f"'{gst}' is not a valid GST number.")

    # Address (optional but structured)
    address = data.get("address")
    if address is not None and not isinstance(address, dict):
        errors.append("'address' must be an object.")

    return errors


def validate_update_client(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for PUT /clients/<id> (partial update).

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    if not data:
        errors.append("Request body cannot be empty.")
        return errors

    if "email" in data:
        email = data.get("email", "").strip()
        if not email:
            errors.append("'email' cannot be set to an empty value.")
        elif not _EMAIL_RE.match(email):
            errors.append(f"'{email}' is not a valid email address.")

    if "phone" in data:
        phone = data.get("phone", "").strip()
        if not phone:
            errors.append("'phone' cannot be set to an empty value.")
        elif not _PHONE_RE.match(phone):
            errors.append(f"'{phone}' is not a valid phone number.")

    if "website" in data:
        website = data.get("website", "").strip()
        if website and not _URL_RE.match(website):
            errors.append(f"'{website}' is not a valid website URL.")

    if "gst_number" in data:
        gst = data.get("gst_number", "").strip()
        if gst and not _GST_RE.match(gst):
            errors.append(f"'{gst}' is not a valid GST number.")

    if "status" in data:
        status = data.get("status", "")
        if status not in VALID_STATUSES:
            errors.append(
                f"Invalid status '{status}'. Allowed: {sorted(VALID_STATUSES)}."
            )

    if "address" in data:
        address = data.get("address")
        if address is not None and not isinstance(address, dict):
            errors.append("'address' must be an object.")

    return errors
