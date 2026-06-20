import logging
from datetime import datetime, timezone

from flask import Blueprint, request

from app.configs.env_config import EnvConfig
from app.utils.api_response import success
from app.utils.integration_helper import (
    PortalID,
    call_portal_api,
    verify_webhook_signature,
)

integration_bp = Blueprint("integration", __name__)
logger = logging.getLogger(__name__)

_portal_webhooks = {}


def register_webhook(portal_name, event_type, url, secret):
    if portal_name not in _portal_webhooks:
        _portal_webhooks[portal_name] = []
    _portal_webhooks[portal_name].append({
        "event_type": event_type,
        "url": url,
        "secret": secret,
    })


def dispatch_event(portal_name, event_type, payload):
    results = []
    webhooks = _portal_webhooks.get(portal_name, [])
    for webhook in [w for w in webhooks if w["event_type"] == event_type]:
        body = {"event": event_type, "payload": payload}
        try:
            call_portal_api(
                PortalID(portal_name), "POST",
                webhook["url"],
                json_data=body,
            )
            results.append({"url": webhook["url"], "status": "delivered"})
        except Exception as e:
            logger.error(f"Webhook dispatch failed to {webhook['url']}: {e}")
            results.append({"url": webhook["url"], "status": "failed"})
    return results


# ────────────────────────────────────────────
# PORTAL 1 — Project Request Integration
# ────────────────────────────────────────────

def portal1_sync_request(project_data):
    """Sync a project request to Portal 1."""
    return call_portal_api(
        PortalID.PORTAL_1, "POST", "/api/project-requests",
        json_data={
            "source": "portal5",
            "type": "project_request.sync",
            "data": _map_project_request(project_data),
        },
    )


def portal1_create_lead(lead_data):
    """Trigger lead creation in Portal 1."""
    return call_portal_api(
        PortalID.PORTAL_1, "POST", "/api/leads",
        json_data={
            "source": "portal5",
            "type": "lead.created",
            "data": {
                "lead_id": lead_data.get("_id", ""),
                "name": lead_data.get("name", ""),
                "email": lead_data.get("email", ""),
                "phone": lead_data.get("phone", ""),
                "source": "crm-portal5",
            },
        },
    )


def portal1_track_request(request_id):
    """Fetch request tracking status from Portal 1."""
    return call_portal_api(
        PortalID.PORTAL_1, "GET", f"/api/project-requests/{request_id}/track",
    )


def _map_project_request(crm_data):
    """Data mapping: CRM data → Portal 1 project request format."""
    return {
        "external_id": crm_data.get("_id", ""),
        "title": crm_data.get("name", crm_data.get("title", "")),
        "requester": crm_data.get("email", ""),
        "description": crm_data.get("description", ""),
        "priority": crm_data.get("priority", "medium"),
        "source_system": "portal5-crm",
    }


# ────────────────────────────────────────────
# PORTAL 3 — Workspace Integration
# ────────────────────────────────────────────

def portal3_create_workspace(client_data):
    """Create a workspace in Portal 3 for a new client."""
    return call_portal_api(
        PortalID.PORTAL_3, "POST", "/api/workspaces",
        json_data={
            "source": "portal5",
            "type": "workspace.create",
            "data": {
                "client_id": client_data.get("_id", ""),
                "client_name": client_data.get("name", ""),
                "client_email": client_data.get("email", ""),
                "company": client_data.get("company", ""),
                "owner_id": client_data.get("owner_id", ""),
            },
        },
    )


def portal3_associate_project(proposal_data):
    """Associate a project with a workspace in Portal 3."""
    return call_portal_api(
        PortalID.PORTAL_3, "POST", "/api/projects",
        json_data={
            "source": "portal5",
            "type": "project.associate",
            "data": {
                "proposal_id": proposal_data.get("_id", ""),
                "client_id": proposal_data.get("client_id", ""),
                "title": proposal_data.get("title", ""),
                "amount": proposal_data.get("amount", 0),
                "status": proposal_data.get("status", "pending"),
            },
        },
    )


def portal3_sync_progress(progress_data):
    """Push progress updates to Portal 3."""
    return call_portal_api(
        PortalID.PORTAL_3, "PUT", "/api/progress",
        json_data={
            "source": "portal5",
            "type": "progress.sync",
            "data": progress_data,
        },
    )


# ────────────────────────────────────────────
# PORTAL 8 — Automation Integration
# ────────────────────────────────────────────

def portal8_trigger_workflow(event_type, context):
    """Trigger an automation workflow in Portal 8."""
    return call_portal_api(
        PortalID.PORTAL_8, "POST", "/api/workflows/trigger",
        json_data={
            "source": "portal5",
            "type": "workflow.trigger",
            "data": {
                "event": event_type,
                "context": context,
                "timestamp": str(datetime.now(timezone.utc)),
            },
        },
    )


def portal8_send_notification(notification):
    """Send a notification via Portal 8 automation."""
    return call_portal_api(
        PortalID.PORTAL_8, "POST", "/api/notifications",
        json_data={
            "source": "portal5",
            "type": "notification.send",
            "data": notification,
        },
    )


def portal8_emit_crm_event(event_name, payload):
    """Emit a CRM automation event to Portal 8."""
    return call_portal_api(
        PortalID.PORTAL_8, "POST", "/api/events",
        json_data={
            "source": "portal5",
            "type": "crm.event",
            "data": {
                "event": event_name,
                "payload": payload,
                "timestamp": str(datetime.now(timezone.utc)),
            },
        },
    )


def portal8_sync_activity(activity_data):
    """Sync CRM activity to Portal 8 automation logs."""
    return call_portal_api(
        PortalID.PORTAL_8, "POST", "/api/activities",
        json_data={
            "source": "portal5",
            "type": "activity.sync",
            "data": activity_data,
        },
    )


# ────────────────────────────────────────────
# PORTAL 6 — Performance Integration
# ────────────────────────────────────────────

def portal6_push_metrics(metrics_data):
    """Push project delivery metrics to Performance portal."""
    return call_portal_api(
        PortalID.PORTAL_6, "POST", "/api/metrics",
        json_data={
            "source": "portal5",
            "type": "delivery.metrics",
            "data": metrics_data,
        },
    )


def portal6_track_completion(project_id, completed_at=None):
    """Report project completion to Performance portal."""
    return call_portal_api(
        PortalID.PORTAL_6, "PUT", f"/api/projects/{project_id}/complete",
        json_data={
            "source": "portal5",
            "type": "project.completed",
            "data": {
                "project_id": project_id,
                "completed_at": completed_at or str(datetime.now(timezone.utc)),
                "source_system": "portal5-crm",
            },
        },
    )


def portal6_push_score(score_data):
    """Push performance scoring data to Portal 6."""
    return call_portal_api(
        PortalID.PORTAL_6, "POST", "/api/scores",
        json_data={
            "source": "portal5",
            "type": "performance.score",
            "data": score_data,
        },
    )


# ────────────────────────────────────────────
# WEBHOOK RECEIVER — Incoming events from portals
# ────────────────────────────────────────────

_EVENT_ROUTERS = {}


def register_event_handler(event_type, handler_fn):
    _EVENT_ROUTERS[event_type] = handler_fn


@integration_bp.route("/webhook", methods=["POST"])
def receive_webhook():
    signature = request.headers.get("X-Webhook-Signature", "")
    portal_name = request.headers.get("X-Portal-Name", "unknown")
    timestamp = request.headers.get("X-Request-Timestamp", "")
    payload = request.get_data(as_text=True)

    if not verify_webhook_signature(payload, signature, EnvConfig.PORTAL_WEBHOOK_SECRET):
        logger.warning(f"Invalid webhook signature from portal: {portal_name}")
        from app.utils.api_response import unauthorized
        return unauthorized(message="Invalid webhook signature")

    if not timestamp:
        logger.warning(f"Missing timestamp header from {portal_name}")
        from app.utils.api_response import unauthorized
        return unauthorized(message="Missing timestamp header")

    try:
        ts = datetime.fromisoformat(timestamp)
        age = datetime.now(timezone.utc) - ts
        if abs(age.total_seconds()) > 60:
            age_secs = int(age.total_seconds())
            logger.warning(f"Webhook replay detected from {portal_name}: age={age_secs}s")
            from app.utils.api_response import unauthorized
            return unauthorized(message="Webhook expired")
    except (ValueError, TypeError):
        logger.warning(f"Invalid timestamp in webhook from {portal_name}: {timestamp}")
        from app.utils.api_response import unauthorized
        return unauthorized(message="Invalid timestamp format")

    data = request.get_json(silent=True) or {}
    event_type = data.get("event", "unknown")
    event_payload = data.get("data", {})

    handler = _EVENT_ROUTERS.get(event_type)
    if handler:
        try:
            handler(event_payload, portal_name)
        except Exception:
            logger.exception(f"Handler failed for {event_type}")
            from app.utils.api_response import internal_error
            return internal_error(message="Event handler error", code="HANDLER_ERROR")

    return success(data={"event": event_type}, message="Webhook received")
