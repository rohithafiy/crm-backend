"""
Portal 5 - CRM & Client Management
Pipeline Validator: Stage transition rules and update validation

Author: P5-A2 (CRM Backend Engineer)
"""

from typing import Any

from app.models.p5_lead import LeadStatus, VALID_TRANSITIONS

VALID_STAGES = {s.value for s in LeadStatus}


def validate_stage_transition(
    current_status: str,
    new_status: str,
) -> list[str]:
    """
    Validate that a pipeline stage transition is permitted.

    Allowed transitions::

        new          → contacted, lost
        contacted    → qualified, lost
        qualified    → proposal_sent, lost
        proposal_sent → negotiation, lost
        negotiation  → won, lost
        won          → (terminal)
        lost         → (terminal)

    Args:
        current_status: The lead's current pipeline stage
        new_status: Requested target stage

    Returns:
        List of error strings (empty = valid transition)
    """
    errors: list[str] = []

    if new_status not in VALID_STAGES:
        errors.append(
            f"'{new_status}' is not a valid pipeline stage. "
            f"Allowed: {sorted(VALID_STAGES)}."
        )
        return errors

    allowed_next = VALID_TRANSITIONS.get(current_status, [])

    if new_status == current_status:
        errors.append(f"Lead is already at stage '{current_status}'.")
        return errors

    if not allowed_next:
        errors.append(
            f"Stage '{current_status}' is a terminal state and cannot be changed."
        )
        return errors

    if new_status not in allowed_next:
        errors.append(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed next stages: {allowed_next}."
        )

    return errors


def validate_pipeline_update(data: dict[str, Any]) -> list[str]:
    """
    Validate payload for PUT /pipeline/<lead_id>.

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    if not data:
        errors.append("Request body cannot be empty.")
        return errors

    status = data.get("status", "").strip()
    if not status:
        errors.append("'status' is required.")
    elif status not in VALID_STAGES:
        errors.append(
            f"Invalid stage '{status}'. Allowed: {sorted(VALID_STAGES)}."
        )

    return errors
