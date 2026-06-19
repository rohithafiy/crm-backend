class SecurityConfig:
    BCRYPT_ROUNDS = 12
    JWT_ALGORITHM = "HS256"

    ALLOWED_ROLES = ["super_admin", "ops_lead", "project_manager", "client"]

    ROLE_HIERARCHY = {
        "super_admin": ["ops_lead", "project_manager", "client"],
        "ops_lead": ["project_manager", "client"],
        "project_manager": ["client"],
        "client": [],
    }

    PERMISSIONS = {
        "leads:read": ["super_admin", "ops_lead", "project_manager"],
        "leads:write": ["super_admin", "ops_lead"],
        "leads:delete": ["super_admin"],
        "leads:assign": ["super_admin", "ops_lead"],
        "clients:read": ["super_admin", "ops_lead", "project_manager", "client"],
        "clients:write": ["super_admin", "ops_lead"],
        "clients:delete": ["super_admin"],
        "clients:assign": ["super_admin", "ops_lead"],
        "proposals:read": ["super_admin", "ops_lead", "project_manager", "client"],
        "proposals:write": ["super_admin", "ops_lead", "project_manager"],
        "proposals:delete": ["super_admin"],
        "proposals:approve": ["super_admin", "ops_lead", "project_manager"],
        "invoices:read": ["super_admin", "ops_lead", "project_manager", "client"],
        "invoices:write": ["super_admin", "ops_lead"],
        "invoices:delete": ["super_admin"],
        "invoices:approve": ["super_admin", "ops_lead"],
        "payments:read": ["super_admin", "ops_lead", "project_manager", "client"],
        "payments:write": ["super_admin", "ops_lead"],
        "payments:delete": ["super_admin"],
        "payments:refund": ["super_admin", "ops_lead"],
        "analytics:read": ["super_admin", "ops_lead", "project_manager"],
        "analytics:export": ["super_admin", "ops_lead"],
        "admin:users": ["super_admin"],
        "admin:roles": ["super_admin"],
        "admin:settings": ["super_admin"],
        "admin:audit": ["super_admin"],
    }

    PUBLIC_ROUTES = [
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/health",
        "/integration/webhook",
    ]

    @classmethod
    def is_public_route(cls, path):
        return path in cls.PUBLIC_ROUTES
