import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.utils.jwt_helper import create_access_token, create_refresh_token
from app.utils.permission_helper import verify_client_ownership
from app.utils.audit_helper import log_audit

# Helper for mocking MongoDB with mongomock if needed, or using MagicMocks
def make_mock_db():
    from mongomock import MongoClient
    client = MongoClient()
    db = client.db
    # Seed default user
    db.users.insert_one({
        "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d0e"),
        "email": "test@example.com",
        "password_hash": "$2b$12$dummyhash",
        "role": "client",
        "roles": ["client"],
        "is_active": True
    })
    return db


# ─── 1. Cookie & JWT Storage Contract Verification ──────────────────────────

class TestJWTCookieSecurity:
    @patch("app.utils.db.get_db")
    def test_login_sets_httponly_secure_strict_cookies(self, mock_get_db, client):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        with patch("bcrypt.checkpw", return_value=True):
            resp = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "SecurePassword1"
            })
            
        assert resp.status_code == 200
        cookies = resp.headers.getlist("Set-Cookie")
        
        # Verify that access_token cookie is present and properly hardened
        access_cookie = [c for c in cookies if "access_token=" in c][0]
        assert "HttpOnly" in access_cookie
        assert "Secure" in access_cookie
        assert "SameSite=Strict" in access_cookie
        
        # Verify that token is not exposed in JSON response body
        body = resp.get_json()
        assert "access_token" not in body
        assert "refresh_token" not in body


# ─── 2. Client Isolation Verification ────────────────────────────────────────

class TestClientIsolation:
    @patch("app.utils.db.get_db")
    def test_verify_client_ownership_logic(self, mock_get_db, app):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        client_a_id = "665a1b2c3d4e5f6a7b8c9d0e"
        client_b_id = str(ObjectId())
        
        # Insert a project owned by Client A
        proj_id = db.client_projects.insert_one({
            "title": "Client A Project",
            "owner_id": client_a_id
        }).inserted_id
        
        with app.test_request_context():
            from flask import g
            # Client A tries to access Client A Project
            g.roles = ["client"]
            assert verify_client_ownership(client_a_id, "client_projects", str(proj_id)) is True
            
            # Client B tries to access Client A Project
            assert verify_client_ownership(client_b_id, "client_projects", str(proj_id)) is False
            
            # Admin tries to access Client A Project
            g.roles = ["super_admin"]
            assert verify_client_ownership(client_b_id, "client_projects", str(proj_id)) is True

    @patch("app.utils.db.get_db")
    def test_client_endpoints_enforce_ownership(self, mock_get_db, client):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        # Insert resource owned by Client A
        client_a_id = "665a1b2c3d4e5f6a7b8c9d0e"
        proj_id = db.client_projects.insert_one({
            "title": "A's Project",
            "owner_id": client_a_id
        }).inserted_id
        
        # Create token for Client B
        client_b_id = str(ObjectId())
        token, _ = create_access_token(client_b_id, "client")
        client.set_cookie("access_token", token)
        
        # Client B tries to update Client A's project
        resp = client.put(f"/api/client/projects/{proj_id}", json={"title": "Hacked Title"})
        assert resp.status_code == 403
        
        # Client B tries to delete Client A's project
        resp = client.delete(f"/api/client/projects/{proj_id}")
        assert resp.status_code == 403


# ─── 3. Rate Limiting Verification ──────────────────────────────────────────

class TestRateLimiter:
    @patch("app.utils.db.get_db")
    def test_login_rate_limiting(self, mock_get_db, client):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        # Import limiter to reset key store before test
        from app.utils.limiter import limiter
        limiter.reset()
        
        # Hit login endpoint 5 times (all fail)
        with patch("bcrypt.checkpw", return_value=False):
            for _ in range(5):
                resp = client.post("/api/auth/login", json={
                    "email": "test@example.com",
                    "password": "wrongpassword"
                })
                assert resp.status_code == 401
            
            # 6th attempt should be blocked by rate limiting (429)
            resp = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            assert resp.status_code == 429
            body = resp.get_json()
            assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"



# ─── 4. CRM Settings & RBAC Verification ─────────────────────────────────────

class TestCRMSettingsRBAC:
    @patch("app.utils.db.get_db")
    def test_crm_settings_restricted_to_admin(self, mock_get_db, client):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        # 1. Logged in as Client -> Access Forbidden
        token, _ = create_access_token("665a1b2c3d4e5f6a7b8c9d0e", "client")
        client.set_cookie("access_token", token)
        
        resp = client.get("/api/crm/settings")
        assert resp.status_code == 403
        
        # 2. Logged in as super_admin -> Access Allowed
        admin_token, _ = create_access_token(str(ObjectId()), "super_admin")
        client.set_cookie("access_token", admin_token)
        
        resp = client.get("/api/crm/settings")
        assert resp.status_code == 200


# ─── 5. Compliance Audit Logs Verification ────────────────────────────────────

class TestComplianceAuditLogging:
    @patch("app.utils.db.get_db")
    def test_audit_logs_created_on_critical_actions(self, mock_get_db, client):
        db = make_mock_db()
        mock_get_db.return_value = db
        
        # Log in as super_admin to perform settings update
        admin_token, _ = create_access_token(str(ObjectId()), "super_admin")
        client.set_cookie("access_token", admin_token)
        
        # Perform action: Update tax settings
        resp = client.put("/api/crm/settings/tax-settings", json={
            "default_tax_rate": 12.5,
            "tax_id": "GSTIN-TEST"
        })
        assert resp.status_code == 200
        
        # Query audit_logs collection
        audit_records = list(db.audit_logs.find({"action": "tax_settings_update"}))
        assert len(audit_records) == 1
        assert audit_records[0]["action"] == "tax_settings_update"
        assert "timestamp" in audit_records[0]
        assert "actor" in audit_records[0]
