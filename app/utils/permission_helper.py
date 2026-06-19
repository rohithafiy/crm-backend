from functools import wraps

from bson.objectid import ObjectId
from flask import g

from app.utils import db as _db
from app.utils.api_response import forbidden, not_found
from app.utils.role_helper import has_any_role, has_permission


def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_permission(getattr(g, "roles", []), permission):
                return forbidden(
                    message="Insufficient permissions",
                    code="INSUFFICIENT_PERMISSIONS",
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_roles(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_roles = getattr(g, "roles", [])
            if not has_any_role(user_roles, roles):
                return forbidden(
                    message="Insufficient role",
                    code="INSUFFICIENT_ROLE",
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_ownership(resource_type, id_field="id", owner_field="owner_id"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, "user_id", None)
            user_roles = getattr(g, "roles", [])
            resource_id = kwargs.get(id_field)

            if not resource_id:
                return not_found(message=f"No {id_field} provided")

            if has_any_role(user_roles, ["super_admin", "ops_lead"]):
                return f(*args, **kwargs)

            db = _db.get_db()
            try:
                doc = db[resource_type].find_one({"_id": ObjectId(resource_id)})
            except Exception:
                return not_found(message=f"{resource_type.capitalize()} not found")

            if not doc:
                return not_found(message=f"{resource_type.capitalize()} not found")

            doc_owner = str(doc.get(owner_field, ""))
            if doc_owner and doc_owner != user_id:
                return forbidden(
                    message="You do not own this resource",
                    code="FORBIDDEN",
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator
