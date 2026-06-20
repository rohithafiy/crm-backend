# API Governance Standards

## Versioning

All endpoints are versioned via URL prefix:

```
/api/auth/login
/api/v1/leads
/api/v1/clients
```

Current version: **v1** — `application/vnd.lti-crm.v1+json`

---

## Standard Success Response Envelope

Every successful response follows this structure:

```json
{
  "status": "success",
  "code": 200,
  "data": { ... },
  "message": "Optional success message",
  "metadata": {
    "api_version": "v1",
    "timestamp": "2026-06-18T12:00:00.000000+00:00"
  }
}
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"success"` |
| `code` | `int` | HTTP status code |
| `data` | `object\|array` | Response payload |
| `message` | `string\|null` | Optional human-readable message |
| `metadata` | `object` | Version and timestamp |

### 201 Created
```json
{
  "status": "success",
  "code": 201,
  "data": { "id": "665a...", ... },
  "message": "Resource created",
  "metadata": { "api_version": "v1", "timestamp": "..." }
}
```

---

## Paginated Response

List endpoints that support pagination return:

```json
{
  "status": "success",
  "code": 200,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "..."
  }
}
```

The `X-Total-Count` header is also set with the total count.

---

## Standard Error Response Envelope

```json
{
  "status": "error",
  "code": 401,
  "error": {
    "type": "authentication_error",
    "code": "AUTH_ERROR",
    "message": "Authentication required",
    "details": {}
  },
  "metadata": {
    "api_version": "v1",
    "timestamp": "..."
  }
}
```

### Error Types and Codes

| HTTP | Error Type | Error Codes |
|------|-----------|-------------|
| **400** | `validation_error` | `MISSING_FIELD`, `INVALID_FIELD`, `INVALID_ROLE` |
| **401** | `authentication_error` | `AUTH_ERROR`, `INVALID_CREDENTIALS`, `USER_NOT_FOUND` |
| **403** | `authorization_error` | `INSUFFICIENT_PERMISSIONS`, `INSUFFICIENT_ROLE`, `ACCOUNT_DEACTIVATED` |
| **404** | `not_found` | `RESOURCE_NOT_FOUND` |
| **409** | `conflict` | `RESOURCE_CONFLICT`, `EMAIL_EXISTS` |
| **429** | `rate_limit` | `RATE_LIMIT_EXCEEDED` |
| **500** | `system_error` | `INTERNAL_ERROR` |

---

## Endpoint Conventions

### Naming
- **Plural nouns** for collections: `/leads`, `/clients`, `/proposals`
- **Resource ID** in path: `/leads/{lead_id}`
- **Actions** as sub-resources: `/leads/{lead_id}/assign`
- **Snake case** for JSON field names: `client_id`, `due_date`, `owner_id`

### HTTP Methods
| Method | Behavior | Idempotent |
|--------|----------|------------|
| `GET` | Retrieve resource(s) | ✅ Yes |
| `POST` | Create resource | ❌ No |
| `PUT` | Full/partial update | ✅ Yes |
| `DELETE` | Remove resource | ✅ Yes |

### Request Standards
- Content-Type: `application/json`
- Authorization: `Bearer <JWT>` or HTTP-only cookie `access_token` (except public routes)
- Dates: ISO 8601 UTC (`2026-06-18T12:00:00Z`)

### Response Standards
- Always use the standard envelope
- Status codes match HTTP semantics
- Errors include machine-readable `code` for client logic
- No sensitive data (passwords, tokens) in error messages
- JWT tokens are set as HTTP-only, Secure, SameSite cookies — never exposed in JSON responses

---

## Utility Reference

The API governance system is implemented in `app/utils/api_response.py`:

### Success Helpers
| Function | HTTP Code | Usage |
|----------|-----------|-------|
| `success(data, message)` | **200** | Standard success |
| `created(data, message)` | **201** | Resource created |
| `paginated(data, page, per_page, total)` | **200** | Paginated list |

### Error Helpers
| Function | HTTP Code | Default Error Code |
|----------|-----------|-------------------|
| `bad_request(message, code)` | **400** | `VALIDATION_ERROR` |
| `unauthorized(message)` | **401** | `AUTH_ERROR` |
| `forbidden(message, code)` | **403** | `INSUFFICIENT_PERMISSIONS` |
| `not_found(message, code)` | **404** | `RESOURCE_NOT_FOUND` |
| `conflict(message, code)` | **409** | `RESOURCE_CONFLICT` |
| `too_many_requests(message, code)` | **429** | `RATE_LIMIT_EXCEEDED` |
| `internal_error(message, code)` | **500** | `INTERNAL_ERROR` |

All helpers automatically attach `metadata.api_version` and `metadata.timestamp` to every response.
