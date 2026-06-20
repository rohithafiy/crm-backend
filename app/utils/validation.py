import re

from flask import request

from app.utils.api_response import bad_request


class ValidationRule:
    def __init__(self, field, required=False, field_type=str, min_len=None,
                 max_len=None, pattern=None, enum=None, min_value=None,
                 max_value=None, message=None):
        self.field = field
        self.required = required
        self.field_type = field_type
        self.min_len = min_len
        self.max_len = max_len
        self.pattern = pattern
        self.enum = enum
        self.min_value = min_value
        self.max_value = max_value
        self.message = message

    def validate(self, data):
        value = data.get(self.field)

        if self.required and value is None:
            return self.message or f"'{self.field}' is required"

        if value is None:
            return None

        if self.enum and value not in self.enum:
            valid = ", ".join(str(e) for e in self.enum)
            return self.message or f"'{self.field}' must be one of: {valid}"

        if not isinstance(value, self.field_type):
            if isinstance(self.field_type, tuple):
                names = " or ".join(t.__name__ for t in self.field_type)
                expected = names
            else:
                expected = self.field_type.__name__
            return self.message or f"'{self.field}' must be of type {expected}"

        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return self.message or f"'{self.field}' must be at least {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return self.message or f"'{self.field}' must be at most {self.max_value}"

        if isinstance(value, str):
            if self.min_len and len(value) < self.min_len:
                return self.message or f"'{self.field}' must be at least {self.min_len} characters"
            if self.max_len and len(value) > self.max_len:
                return self.message or f"'{self.field}' must be at most {self.max_len} characters"
            if self.pattern and not re.match(self.pattern, value):
                return self.message or f"'{self.field}' format is invalid"

        return None


PASSWORD_RULES = [
    ValidationRule(
        "password", required=True, field_type=str, min_len=8, max_len=128,
        pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]).+$",
        message=(
            "Password must be at least 8 characters with uppercase, "
            "lowercase, a number, and a special character"
        ),
    ),
]

EMAIL_RULES = [
    ValidationRule("email", required=True, field_type=str, max_len=255,
                   pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                   message="A valid email is required"),
]

LOGIN_RULES = EMAIL_RULES + [
    ValidationRule("password", required=True, field_type=str, message="Password is required"),
]


def validate_request(rules, data=None):
    if data is None:
        data = request.get_json(silent=True) or {}

    errors = []
    for rule in rules:
        error = rule.validate(data)
        if error:
            errors.append(error)

    if errors:
        return bad_request(
            message="Validation failed",
            code="VALIDATION_ERROR",
            details={"fields": errors},
        )
    return None
