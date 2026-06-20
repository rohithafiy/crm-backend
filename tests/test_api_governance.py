
from app.utils.api_response import (
    API_VERSION,
    bad_request,
    conflict,
    created,
    forbidden,
    internal_error,
    not_found,
    paginated,
    success,
    too_many_requests,
    unauthorized,
)


class TestSuccessResponseFormat:
    def test_success_envelope_structure(self, app):
        with app.test_request_context():
            resp, code = success(data={"key": "val"}, message="Done")
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["code"] == 200
        assert body["data"] == {"key": "val"}
        assert body["message"] == "Done"
        assert body["metadata"]["api_version"] == "v1"
        assert "timestamp" in body["metadata"]

    def test_created_envelope(self, app):
        with app.test_request_context():
            resp, code = created(data={"id": 1}, message="Created")
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["code"] == 201
        assert body["data"] == {"id": 1}

    def test_paginated_envelope(self, app):
        with app.test_request_context():
            resp, code, headers = paginated(
                data=[{"id": 1}], page=1, per_page=10, total=25,
            )
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["pagination"]["page"] == 1
        assert body["pagination"]["per_page"] == 10
        assert body["pagination"]["total"] == 25
        assert body["pagination"]["total_pages"] == 3
        assert body["pagination"]["has_next"] is True
        assert body["pagination"]["has_prev"] is False
        assert headers["X-Total-Count"] == "25"

    def test_paginated_single_page(self, app):
        with app.test_request_context():
            resp, code, headers = paginated([], 1, 20, 5)
        body = resp.get_json()
        assert body["pagination"]["total_pages"] == 1
        assert body["pagination"]["has_next"] is False
        assert body["pagination"]["has_prev"] is False


class TestErrorResponseFormat:
    def test_bad_request(self, app):
        with app.test_request_context():
            resp, code = bad_request(message="Missing field", code="MISSING_FIELD")
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["code"] == 400
        assert body["error"]["type"] == "validation_error"
        assert body["error"]["code"] == "MISSING_FIELD"
        assert body["error"]["message"] == "Missing field"
        assert isinstance(body["error"]["details"], dict)

    def test_unauthorized(self, app):
        with app.test_request_context():
            resp, code = unauthorized()
        body = resp.get_json()
        assert body["code"] == 401
        assert body["error"]["type"] == "authentication_error"
        assert body["error"]["code"] == "AUTH_ERROR"
        assert body["error"]["message"] == "Authentication required"

    def test_forbidden(self, app):
        with app.test_request_context():
            resp, code = forbidden(code="INSUFFICIENT_ROLE")
        body = resp.get_json()
        assert body["code"] == 403
        assert body["error"]["type"] == "authorization_error"

    def test_not_found(self, app):
        with app.test_request_context():
            resp, code = not_found()
        body = resp.get_json()
        assert body["code"] == 404
        assert body["error"]["type"] == "not_found"

    def test_conflict(self, app):
        with app.test_request_context():
            resp, code = conflict(code="EMAIL_EXISTS")
        body = resp.get_json()
        assert body["code"] == 409
        assert body["error"]["type"] == "conflict"

    def test_too_many_requests(self, app):
        with app.test_request_context():
            resp, code = too_many_requests()
        body = resp.get_json()
        assert body["code"] == 429
        assert body["error"]["type"] == "rate_limit"

    def test_internal_error(self, app):
        with app.test_request_context():
            resp, code = internal_error()
        body = resp.get_json()
        assert body["code"] == 500
        assert body["error"]["type"] == "system_error"

    def test_error_with_details(self, app):
        with app.test_request_context():
            resp, code = bad_request(
                message="Invalid email",
                code="INVALID_FIELD",
                details={"field": "email", "value": "not-an-email"},
            )
        body = resp.get_json()
        assert body["error"]["details"]["field"] == "email"
        assert body["error"]["details"]["value"] == "not-an-email"

    def test_metadata_in_errors(self, app):
        with app.test_request_context():
            resp, code = bad_request()
        body = resp.get_json()
        assert body["metadata"]["api_version"] == API_VERSION
        assert "timestamp" in body["metadata"]


class TestGovernanceCompliance:
    def test_health_endpoint_uses_envelope(self, client):
        resp = client.get("/health")
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["code"] == 200
        assert body["data"]["status"] == "healthy"
        assert "metadata" in body

    def test_auth_error_uses_envelope(self, client):
        resp = client.get("/api/auth/me")
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["code"] == 401
        assert body["error"]["type"] == "authentication_error"
        assert "metadata" in body

    def test_permission_error_uses_envelope(self, app):
        with app.test_request_context():
            from flask import g
            g.roles = ["client"]
            resp, code = forbidden()
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["code"] == 403
        assert body["error"]["type"] == "authorization_error"

    def test_rate_limit_uses_envelope(self, app):
        with app.test_request_context():
            resp, code = too_many_requests()
        body = resp.get_json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
