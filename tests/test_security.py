from app.utils.integration_helper import sign_webhook_payload, verify_webhook_signature


class TestRateLimiting:
    def test_rate_limit_config(self):
        from app.configs.env_config import EnvConfig
        assert EnvConfig.RATE_LIMIT_ENABLED is True
        assert EnvConfig.RATE_LIMIT_REQUESTS > 0
        assert EnvConfig.RATE_LIMIT_WINDOW > 0


class TestSecurityConfig:
    def test_allowed_roles(self):
        from app.configs.security_config import SecurityConfig
        assert "super_admin" in SecurityConfig.ALLOWED_ROLES
        assert "ops_lead" in SecurityConfig.ALLOWED_ROLES
        assert "project_manager" in SecurityConfig.ALLOWED_ROLES
        assert "client" in SecurityConfig.ALLOWED_ROLES

    def test_role_hierarchy(self):
        from app.configs.security_config import SecurityConfig
        assert "ops_lead" in SecurityConfig.ROLE_HIERARCHY["super_admin"]
        assert "client" in SecurityConfig.ROLE_HIERARCHY["ops_lead"]
        assert "client" in SecurityConfig.ROLE_HIERARCHY["project_manager"]
        assert SecurityConfig.ROLE_HIERARCHY["client"] == []

    def test_permission_coverage(self):
        from app.configs.security_config import SecurityConfig
        for perm, roles in SecurityConfig.PERMISSIONS.items():
            for role in roles:
                assert role in SecurityConfig.ALLOWED_ROLES, (
                    f"Role {role} in {perm} not in ALLOWED_ROLES"
                )

    def test_public_routes_prefix(self):
        from app.configs.security_config import SecurityConfig
        for route in SecurityConfig.PUBLIC_ROUTES:
            assert route.startswith("/")

    def test_admin_permission_structure(self):
        from app.configs.security_config import SecurityConfig
        for perm in SecurityConfig.PERMISSIONS:
            assert perm.startswith("admin:"), f"Unexpected permission: {perm}"

    def test_super_admin_has_all(self):
        from app.configs.security_config import SecurityConfig
        for perm, roles in SecurityConfig.PERMISSIONS.items():
            assert "super_admin" in roles, f"super_admin missing from {perm}"


class TestWebhookSignature:
    def test_sign_and_verify(self):
        payload = '{"event":"user.created","payload":{"id":"123"}}'
        secret = "test-secret"
        signature = sign_webhook_payload(payload, secret)
        assert verify_webhook_signature(payload, signature, secret) is True

    def test_verify_wrong_secret(self):
        payload = '{"event":"test"}'
        signature = sign_webhook_payload(payload, "correct-secret")
        assert verify_webhook_signature(payload, signature, "wrong-secret") is False

    def test_verify_tampered_payload(self):
        payload = '{"event":"test"}'
        secret = "my-secret"
        signature = sign_webhook_payload(payload, secret)
        assert verify_webhook_signature(payload + "x", signature, secret) is False
