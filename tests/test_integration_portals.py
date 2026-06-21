from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from app.services.integration_service import (
    portal1_create_lead,
    portal1_sync_request,
    portal1_track_request,
    portal3_associate_project,
    portal3_create_workspace,
    portal3_sync_progress,
    portal6_push_metrics,
    portal6_push_score,
    portal6_track_completion,
    portal8_emit_crm_event,
    portal8_send_notification,
    portal8_sync_activity,
    portal8_trigger_workflow,
)
from app.utils.integration_helper import (
    PortalID,
    call_portal_api,
    sign_webhook_payload,
    verify_webhook_signature,
)


class TestPortalAPIClient:
    def test_call_portal_api_includes_auth_headers(self):
        with patch("app.utils.integration_helper.requests.request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"ok": true}'
            mock_response.json.return_value = {"ok": True}
            mock_request.return_value = mock_response

            result = call_portal_api(
                PortalID.PORTAL_1, "POST", "/api/test", json_data={"key": "val"},
            )

            args, kwargs = mock_request.call_args
            assert kwargs["method"] == "POST"
            assert "X-Portal-5-Auth" in kwargs["headers"]
            assert kwargs["headers"]["X-Portal-Name"] == "portal5"
            assert kwargs["json"] == {"key": "val"}
            assert result == {"ok": True}

    def test_call_portal_api_no_direct_db_access(self):
        """Enforce the master rule: no pymongo usage in integration helper."""
        import app.utils.integration_helper as helper
        source = open(helper.__file__).read()
        assert "MongoClient" not in source
        assert "pymongo" not in source

    def test_call_portal_api_retries_on_failure(self):
        with patch("app.utils.integration_helper._call_portal_api") as mock_call:
            mock_call.side_effect = [
                RequestException("fail1"), RequestException("fail2"), {"ok": True},
            ]
            result = call_portal_api(PortalID.PORTAL_1, "GET", "/api/test")
            assert result == {"ok": True}
            assert mock_call.call_count == 3

    def test_call_portal_api_raises_after_max_retries(self):
        with patch("app.utils.integration_helper._call_portal_api") as mock_call:
            mock_call.side_effect = RequestException("always fails")
            with pytest.raises(RequestException):
                call_portal_api(PortalID.PORTAL_1, "GET", "/api/test")
            assert mock_call.call_count == 3


class TestWebhookSignature:
    def test_sign_and_verify_match(self):
        payload = '{"event":"test","data":{"id":"123"}}'
        secret = "shared-secret"
        sig = sign_webhook_payload(payload, secret)
        assert verify_webhook_signature(payload, sig, secret) is True

    def test_verify_rejects_wrong_secret(self):
        payload = '{"event":"test"}'
        sig = sign_webhook_payload(payload, "correct-secret")
        assert verify_webhook_signature(payload, sig, "wrong-secret") is False

    def test_verify_rejects_tampered_payload(self):
        payload = '{"event":"test"}'
        secret = "my-secret"
        sig = sign_webhook_payload(payload, secret)
        assert verify_webhook_signature(payload + "x", sig, secret) is False


class TestPortal1Integration:
    def test_sync_request(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            mock_api.return_value = {"status": "synced", "request_id": "req-001"}
            data = {"_id": "lead-1", "name": "Project Alpha", "email": "a@b.com"}
            result = portal1_sync_request(data)
            assert result["status"] == "synced"
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "project_request.sync"
            assert kwargs["json_data"]["data"]["external_id"] == "lead-1"

    def test_create_lead(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            data = {"_id": "lead-1", "name": "Acme", "email": "a@c.com", "phone": "123"}
            portal1_create_lead(data)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "lead.created"
            assert kwargs["json_data"]["data"]["name"] == "Acme"

    def test_track_request(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            mock_api.return_value = {"status": "in_progress", "pct": 50}
            result = portal1_track_request("req-001")
            assert result["pct"] == 50


class TestPortal3Integration:
    def test_create_workspace(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            data = {"_id": "c-1", "name": "ClientCo", "email": "c@c.com", "company": "CC"}
            portal3_create_workspace(data)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "workspace.create"
            assert kwargs["json_data"]["data"]["client_name"] == "ClientCo"

    def test_associate_project(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            data = {"_id": "p-1", "client_id": "c-1", "title": "Web App", "amount": 5000}
            portal3_associate_project(data)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "project.associate"

    def test_sync_progress(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            data = {"project_id": "p-1", "progress_pct": 75}
            portal3_sync_progress(data)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "progress.sync"


class TestPortal8Integration:
    def test_trigger_workflow(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            portal8_trigger_workflow("lead.assigned", {"lead_id": "l-1"})
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "workflow.trigger"
            assert kwargs["json_data"]["data"]["event"] == "lead.assigned"

    def test_send_notification(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            notif = {"recipient": "user@x.com", "channel": "email", "template": "welcome"}
            portal8_send_notification(notif)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "notification.send"

    def test_emit_crm_event(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            portal8_emit_crm_event("proposal.approved", {"proposal_id": "p-1"})
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "crm.event"

    def test_sync_activity(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            portal8_sync_activity({"user_id": "u-1", "action": "login"})
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "activity.sync"


class TestPortal6Integration:
    def test_push_metrics(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            metrics = {"project_id": "p-1", "milestones_completed": 8, "milestones_total": 10}
            portal6_push_metrics(metrics)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "delivery.metrics"

    def test_track_completion(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            portal6_track_completion("p-1")
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "project.completed"

    def test_push_score(self):
        with patch("app.services.integration_service.call_portal_api") as mock_api:
            score = {"client_id": "c-1", "score_type": "delivery", "score_value": 92.5}
            portal6_push_score(score)
            args, kwargs = mock_api.call_args
            assert kwargs["json_data"]["type"] == "performance.score"


class TestWebhookReceiver:
    def test_receive_valid_webhook(self, client):
        payload = '{"event":"project.request.created","data":{"request_id":"r-1"}}'
        secret = "dev-webhook-secret"
        signature = sign_webhook_payload(payload, secret)
        timestamp = datetime.now(timezone.utc).isoformat()
        resp = client.post(
            "/integration/webhook",
            data=payload,
            content_type="application/json",
            headers={
                "X-Portal-Name": "portal1",
                "X-Webhook-Signature": signature,
                "X-Request-Timestamp": timestamp,
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["event"] == "project.request.created"

    def test_receive_invalid_signature(self, client):
        resp = client.post(
            "/integration/webhook",
            data='{"event":"test"}',
            content_type="application/json",
            headers={
                "X-Portal-Name": "portal1",
                "X-Webhook-Signature": "invalid",
            },
        )
        assert resp.status_code == 401

    def test_receive_routes_to_registered_handler(self, client):
        handler_called = []
        from app.services.integration_service import register_event_handler

        def handler(data, portal):
            handler_called.append((data, portal))

        register_event_handler("test.event", handler)

        payload = '{"event":"test.event","data":{"key":"val"}}'
        secret = "dev-webhook-secret"
        signature = sign_webhook_payload(payload, secret)
        timestamp = datetime.now(timezone.utc).isoformat()
        resp = client.post(
            "/integration/webhook",
            data=payload,
            content_type="application/json",
            headers={
                "X-Portal-Name": "portal3",
                "X-Webhook-Signature": signature,
                "X-Request-Timestamp": timestamp,
            },
        )
        assert resp.status_code == 200
        assert len(handler_called) == 1
        assert handler_called[0][0] == {"key": "val"}
        assert handler_called[0][1] == "portal3"
