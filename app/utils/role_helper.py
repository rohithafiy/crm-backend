from app.configs.security_config import SecurityConfig


def has_role(user_roles, required_role):
    for role in user_roles:
        if role == required_role:
            return True
        inherited = SecurityConfig.ROLE_HIERARCHY.get(role, [])
        if required_role in inherited:
            return True
    return False


def has_any_role(user_roles, required_roles):
    return any(has_role(user_roles, r) for r in required_roles)


def has_permission(user_roles, permission):
    allowed_roles = SecurityConfig.PERMISSIONS.get(permission, [])
    return has_any_role(user_roles, allowed_roles)


def validate_role(role):
    return role in SecurityConfig.ALLOWED_ROLES
