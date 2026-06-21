from flask import g

from app.utils.permission_helper import require_permission, require_roles
from app.utils.role_helper import has_any_role, has_permission, has_role, validate_role


class TestRoleHelper:
    def test_has_role_direct(self):
        assert has_role(["super_admin"], "super_admin") is True

    def test_has_role_inherited(self):
        assert has_role(["super_admin"], "ops_lead") is True
        assert has_role(["ops_lead"], "client") is True

    def test_has_role_no_match(self):
        assert has_role(["client"], "super_admin") is False
        assert has_role(["project_manager"], "super_admin") is False

    def test_has_any_role(self):
        assert has_any_role(["ops_lead"], ["super_admin", "ops_lead"]) is True
        assert has_any_role(["client"], ["super_admin", "ops_lead"]) is False

    def test_validate_role(self):
        assert validate_role("super_admin") is True
        assert validate_role("ops_lead") is True
        assert validate_role("project_manager") is True
        assert validate_role("client") is True
        assert validate_role("superadmin") is False
        assert validate_role("admin") is False


class TestPermissionHelper:
    def test_super_admin_has_all_admin_permissions(self):
        assert has_permission(["super_admin"], "admin:users") is True
        assert has_permission(["super_admin"], "admin:roles") is True
        assert has_permission(["super_admin"], "admin:settings") is True
        assert has_permission(["super_admin"], "admin:audit") is True

    def test_ops_lead_permissions(self):
        assert has_permission(["ops_lead"], "admin:users") is False

    def test_project_manager_permissions(self):
        assert has_permission(["project_manager"], "admin:settings") is False

    def test_client_limited_permissions(self):
        assert has_permission(["client"], "admin:users") is False
        assert has_permission(["client"], "admin:audit") is False

    def test_permission_denied(self):
        assert has_permission(["client"], "admin:users") is False


class TestPermissionDecorators:
    def test_require_permission_allowed(self, app):
        with app.test_request_context():
            g.roles = ["super_admin"]
            result = require_permission("admin:users")(lambda: "ok")()
            assert result == "ok"

    def test_require_permission_denied(self, app):
        with app.test_request_context():
            g.roles = ["client"]
            resp = require_permission("admin:users")(lambda: "ok")()
            assert resp[1] == 403

    def test_require_roles_allowed(self, app):
        with app.test_request_context():
            g.roles = ["ops_lead"]
            result = require_roles(["super_admin", "ops_lead"])(lambda: "ok")()
            assert result == "ok"

    def test_require_roles_denied(self, app):
        with app.test_request_context():
            g.roles = ["client"]
            resp = require_roles(["super_admin", "ops_lead"])(lambda: "ok")()
            assert resp[1] == 403
