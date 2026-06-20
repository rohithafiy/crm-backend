from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import jwt
from bson.objectid import ObjectId

from app.configs.env_config import EnvConfig
from app.configs.security_config import SecurityConfig
from app.services.auth_service import _LOCKOUT_CACHE, _check_account_lockout, _clear_login_attempts
from app.utils.jwt_helper import create_access_token, create_refresh_token, decode_token
from app.utils.role_helper import has_permission, has_role

# ─── Authentication Security ─────────────────────────────────────────────────


class TestJWTSecurity:
    def test_access_token_creation_and_decode(self):
        token, jti = create_access_token("user1", ["ops_lead"], ["portal1"])
        decoded = decode_token(token)
        assert decoded["sub"] == "user1"
        assert decoded["roles"] == ["ops_lead"]
        assert decoded["role"] == "ops_lead"
        assert decoded["portals"] == ["portal1"]
        assert decoded["type"] == "access"
        assert decoded["jti"] == jti
        assert "iat" in decoded
        assert "exp" in decoded

    def test_access_token_role_fallback(self):
        token, _ = create_access_token("user1", [])
        decoded = decode_token(token)
        assert decoded["role"] == "client"

    def test_refresh_token_creation_and_decode(self):
        token, jti = create_refresh_token("user1")
        decoded = decode_token(token)
        assert decoded["sub"] == "user1"
        assert decoded["type"] == "refresh"
        assert decoded["jti"] == jti

    def test_token_type_access_vs_refresh(self):
        access, _ = create_access_token("u1", ["client"])
        refresh, _ = create_refresh_token("u1")
        assert decode_token(access)["type"] == "access"
        assert decode_token(refresh)["type"] == "refresh"

    def test_expired_token_returns_none(self):
        payload = {
            "sub": "user1", "type": "access", "jti": str(uuid4()),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, EnvConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
        assert decode_token(token) is None

    def test_invalid_signature_returns_none(self):
        payload = {
            "sub": "user1", "type": "access", "jti": str(uuid4()),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "different-secret", algorithm=SecurityConfig.JWT_ALGORITHM)
        assert decode_token(token) is None

    def test_malformed_token_returns_none(self):
        assert decode_token("not.a.token") is None
        assert decode_token("") is None

    def test_tampered_token_returns_none(self):
        token, _ = create_access_token("user1", ["client"])
        parts = token.split(".")
        assert decode_token(f"{parts[0]}.{parts[1]}.invalidsignature") is None

    def test_access_token_has_expiry_claim(self):
        token, _ = create_access_token("user1", ["client"])
        decoded = jwt.decode(token, EnvConfig.JWT_SECRET, algorithms=[SecurityConfig.JWT_ALGORITHM],
                             options={"verify_exp": False})
        assert abs((decoded["exp"] - decoded["iat"]) - EnvConfig.JWT_ACCESS_TOKEN_EXPIRY) <= 2

    @patch("app.utils.db.get_db")
    def test_blacklisted_token_detected(self, mock_get_db):
        from app.middleware.auth_middleware import _is_token_blacklisted
        token, jti = create_access_token("u1", ["client"])
        mock_db = MagicMock()
        mock_db.token_blacklist.find_one.return_value = None
        mock_get_db.return_value = mock_db
        assert _is_token_blacklisted(jti) is False
        mock_db.token_blacklist.find_one.return_value = {"jti": jti}
        assert _is_token_blacklisted(jti) is True

    def test_token_unique_jti(self):
        _, jti1 = create_access_token("u1", ["client"])
        _, jti2 = create_access_token("u1", ["client"])
        assert jti1 != jti2

    def test_decode_token_handles_all_error_types(self):
        assert decode_token("") is None
        assert decode_token(None) is None
        assert decode_token("a.b.c") is None


# ─── Authorization Security ──────────────────────────────────────────────────


class TestRoleAndPermission:
    def test_role_hierarchy_enforced(self):
        assert has_role(["super_admin"], "client") is True
        assert has_role(["ops_lead"], "client") is True
        assert has_role(["project_manager"], "client") is True
        assert has_role(["client"], "project_manager") is False
        assert has_role(["client"], "ops_lead") is False
        assert has_role(["client"], "super_admin") is False

    def test_permission_via_hierarchy(self):
        assert has_permission(["super_admin"], "admin:users") is True
        assert has_permission(["ops_lead"], "admin:users") is False
        assert has_permission(["project_manager"], "admin:users") is False
        assert has_permission(["client"], "admin:users") is False

    def test_permission_denied(self):
        assert has_permission(["client"], "admin:settings") is False
        assert has_permission(["project_manager"], "admin:settings") is False
        assert has_permission(["ops_lead"], "admin:settings") is False

    def test_require_permission_decorator_allows(self, app):
        from app.utils.permission_helper import require_permission
        with app.test_request_context():
            from flask import g
            g.roles = ["super_admin"]
            func = Mock()
            require_permission("admin:users")(func)()
            func.assert_called_once()

    def test_require_permission_decorator_denies(self, app):
        from app.utils.permission_helper import require_permission
        with app.test_request_context():
            from flask import g
            g.roles = ["client"]
            func = Mock()
            result = require_permission("admin:users")(func)()
            assert result is not None
            func.assert_not_called()

    def test_require_roles_decorator_uses_hierarchy(self, app):
        from app.utils.permission_helper import require_roles
        with app.test_request_context():
            from flask import g
            g.roles = ["super_admin"]
            func = Mock()
            require_roles(["project_manager"])(func)()
            func.assert_called_once()

    def test_require_roles_decorator_denies(self, app):
        from app.utils.permission_helper import require_roles
        with app.test_request_context():
            from flask import g
            g.roles = ["client"]
            func = Mock()
            result = require_roles(["ops_lead"])(func)()
            assert result is not None
            func.assert_not_called()


class TestResourceOwnership:
    def test_ownership_allows_admin(self, app):
        from app.utils.permission_helper import require_ownership
        with app.test_request_context():
            from flask import g
            g.user_id = "admin1"
            g.roles = ["super_admin"]
            func = Mock()
            require_ownership("users")(func)(id="507f1f77bcf86cd799439011")
            func.assert_called_once()

    @patch("app.utils.db.get_db")
    def test_ownership_allows_owner(self, mock_get_db, app):
        from app.utils.permission_helper import require_ownership
        user_id = str(ObjectId())
        mock_db = MagicMock()
        col_mock = mock_db.__getitem__.return_value
        col_mock.find_one.return_value = {"_id": ObjectId(), "owner_id": user_id}
        mock_get_db.return_value = mock_db
        with app.test_request_context():
            from flask import g
            g.user_id = user_id
            g.roles = ["project_manager"]
            func = Mock()
            require_ownership("users")(func)(id="507f1f77bcf86cd799439011")
            func.assert_called_once()

    @patch("app.utils.db.get_db")
    def test_ownership_denies_non_owner(self, mock_get_db, app):
        from app.utils.permission_helper import require_ownership
        user_id = str(ObjectId())
        mock_db = MagicMock()
        col_mock = mock_db.__getitem__.return_value
        col_mock.find_one.return_value = {"_id": ObjectId(), "owner_id": str(ObjectId())}
        mock_get_db.return_value = mock_db
        with app.test_request_context():
            from flask import g
            g.user_id = user_id
            g.roles = ["project_manager"]
            func = Mock()
            result = require_ownership("users")(func)(id="507f1f77bcf86cd799439011")
            assert result is not None
            func.assert_not_called()

    @patch("app.utils.db.get_db")
    def test_ownership_not_found(self, mock_get_db, app):
        from app.utils.permission_helper import require_ownership
        mock_db = MagicMock()
        col_mock = mock_db.__getitem__.return_value
        col_mock.find_one.return_value = None
        mock_get_db.return_value = mock_db
        with app.test_request_context():
            from flask import g
            g.user_id = str(ObjectId())
            g.roles = ["project_manager"]
            func = Mock()
            result = require_ownership("users")(func)(id="507f1f77bcf86cd799439011")
            assert result is not None
            func.assert_not_called()

    @patch("app.utils.db.get_db")
    def test_verify_client_ownership_allows_owner(self, mock_get_db, app):
        from app.utils.permission_helper import verify_client_ownership
        user_id = str(ObjectId())
        mock_db = MagicMock()
        col_mock = mock_db.__getitem__.return_value
        col_mock.find_one.return_value = {"_id": ObjectId(), "owner_id": user_id}
        mock_get_db.return_value = mock_db
        with app.test_request_context():
            from flask import g
            g.user_id = user_id
            g.roles = ["client"]
            assert verify_client_ownership(user_id, "users", "507f1f77bcf86cd799439011") is True

    @patch("app.utils.db.get_db")
    def test_verify_client_ownership_denies_non_owner(self, mock_get_db, app):
        from app.utils.permission_helper import verify_client_ownership
        user_id = str(ObjectId())
        mock_db = MagicMock()
        col_mock = mock_db.__getitem__.return_value
        col_mock.find_one.return_value = {"_id": ObjectId(), "owner_id": str(ObjectId())}
        mock_get_db.return_value = mock_db
        with app.test_request_context():
            from flask import g
            g.user_id = user_id
            g.roles = ["client"]
            assert verify_client_ownership(user_id, "users", "507f1f77bcf86cd799439011") is False

    def test_verify_client_ownership_bypasses_admin(self, app):
        from app.utils.permission_helper import verify_client_ownership
        with app.test_request_context():
            from flask import g
            g.user_id = "admin1"
            g.roles = ["super_admin"]
            assert verify_client_ownership("admin1", "users", "507f1f77bcf86cd799439011") is True

    def test_ownership_ops_lead_bypasses(self, app):
        from app.utils.permission_helper import require_ownership
        with app.test_request_context():
            from flask import g
            g.user_id = "user1"
            g.roles = ["ops_lead"]
            func = Mock()
            require_ownership("users")(func)(id="507f1f77bcf86cd799439011")
            func.assert_called_once()


# ─── API Security ────────────────────────────────────────────────────────────


class TestInputValidation:
    def test_password_strength_required(self, app):
        from app.utils.validation import PASSWORD_RULES, validate_request
        with app.test_request_context():
            result = validate_request(PASSWORD_RULES, {"password": "short"})
        assert result is not None
        body = result[0].get_json()
        assert body["status"] == "error"

    def test_weak_password_needs_number(self, app):
        from app.utils.validation import PASSWORD_RULES, validate_request
        with app.test_request_context():
            assert validate_request(PASSWORD_RULES, {"password": "OnlyLettersNoDigits"}) is not None

    def test_weak_password_needs_uppercase(self, app):
        from app.utils.validation import PASSWORD_RULES, validate_request
        with app.test_request_context():
            assert validate_request(PASSWORD_RULES, {"password": "lowercaseonly1"}) is not None

    def test_strong_password_passes(self, app):
        from app.utils.validation import PASSWORD_RULES, validate_request
        with app.test_request_context():
            assert validate_request(PASSWORD_RULES, {"password": "ValidP@ss1"}) is None

    def test_email_format_validated(self, app):
        from app.utils.validation import EMAIL_RULES, validate_request
        with app.test_request_context():
            assert validate_request(EMAIL_RULES, {"email": "not-an-email"}) is not None
            assert validate_request(EMAIL_RULES, {"email": "valid@example.com"}) is None

    def test_required_field_missing(self, app):
        from app.utils.validation import ValidationRule, validate_request
        rule = ValidationRule("name", required=True)
        with app.test_request_context():
            result = validate_request([rule], {})
        assert result is not None
        body = result[0].get_json()
        assert "name" in body["error"]["details"]["fields"][0]

    def test_enum_validation(self, app):
        from app.utils.validation import ValidationRule, validate_request
        rule = ValidationRule("status", required=True, enum=["active", "inactive"])
        with app.test_request_context():
            assert validate_request([rule], {"status": "invalid"}) is not None
            assert validate_request([rule], {"status": "active"}) is None


class TestProtectedRoutes:
    def test_health_is_public(self, client):
        assert client.get("/health").status_code == 200

    def test_login_is_public(self, client):
        resp = client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
        body = resp.get_json()
        assert resp.status_code == 401
        assert body["error"]["message"] == "Invalid credentials"

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401

    def test_missing_auth_header_returns_401(self, client):
        assert client.get("/api/auth/me").status_code == 401


# ─── Environment Security ────────────────────────────────────────────────────


class TestEnvironmentSecurity:
    def test_no_hardcoded_secrets_in_source(self):
        source_files = [
            "app/configs/env_config.py", "app/services/auth_service.py",
            "app/middleware/auth_middleware.py", "app/utils/jwt_helper.py",
            "app/utils/integration_helper.py",
        ]
        for filepath in source_files:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            assert "password=" not in content
            assert "mongodb+srv://" not in content


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Strict-Transport-Security") == (
            "max-age=31536000; includeSubDomains"
        )
        assert resp.headers.get("Content-Security-Policy") == "default-src 'self'"

    def test_xss_protection_header(self, client):
        assert client.get("/health").headers.get("X-XSS-Protection") == "0"


# ─── Account Lockout ────────────────────────────────────────────────────────


class TestAccountLockout:
    def _lockout(self, email, times):
        for _ in range(times):
            entry = _LOCKOUT_CACHE.setdefault(
                email, {"attempts": 0, "locked_until": datetime.now(timezone.utc)}
            )
            entry["attempts"] += 1
            if entry["attempts"] >= EnvConfig.ACCOUNT_LOCKOUT_THRESHOLD:
                entry["locked_until"] = datetime.now(timezone.utc) + timedelta(
                    seconds=EnvConfig.ACCOUNT_LOCKOUT_DURATION)

    def test_lockout_after_threshold(self):
        _LOCKOUT_CACHE.clear()
        email = "lockout@example.com"
        self._lockout(email, EnvConfig.ACCOUNT_LOCKOUT_THRESHOLD)
        assert _check_account_lockout(email) is True

    def test_no_lockout_below_threshold(self):
        _LOCKOUT_CACHE.clear()
        email = "no_lockout@example.com"
        self._lockout(email, EnvConfig.ACCOUNT_LOCKOUT_THRESHOLD - 1)
        assert _check_account_lockout(email) is False

    def test_lockout_cleared_after_successful_login(self):
        _LOCKOUT_CACHE.clear()
        email = "clear@example.com"
        self._lockout(email, EnvConfig.ACCOUNT_LOCKOUT_THRESHOLD)
        assert _check_account_lockout(email) is True
        _clear_login_attempts(email)
        assert _check_account_lockout(email) is False


# ─── Full-Journey Authentication ────────────────────────────────────────────


class TestAuthJourney:
    @patch("app.utils.db.get_db")
    def test_full_login_returns_cookies(self, mock_get_db, client):
        from tests.test_auth import mock_db as fake_db
        mdb = fake_db()
        mdb.users.insert_one({
            "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d0e"),
            "email": "journey@example.com",
            "password_hash": "$2b$12$dummyhash",
            "roles": ["client"],
            "portals": [],
            "is_active": True,
        })
        mock_get_db.return_value = mdb
        with patch("bcrypt.checkpw", return_value=True):
            resp = client.post("/api/auth/login", json={
                "email": "journey@example.com", "password": "SecurePass1",
            })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert body.get("data") is None
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert "access_token" in set_cookie
