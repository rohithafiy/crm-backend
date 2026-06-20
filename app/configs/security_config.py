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
        "admin:users": ["super_admin"],
        "admin:roles": ["super_admin"],
        "admin:settings": ["super_admin"],
        "admin:audit": ["super_admin"],
    }

    PUBLIC_ROUTES = [
        "/api/auth/login",
        "/api/auth/refresh",
        "/health",
        "/integration/webhook",
    ]

    @classmethod
    def is_public_route(cls, path):
        return path in cls.PUBLIC_ROUTES
