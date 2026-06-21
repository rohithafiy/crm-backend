# Ownership Enforcement Ledger

## Overview

This document provides a complete enforcement matrix for multi-tenant data isolation in Portal 5.
The security mandate is: **Client A must never access Client B's data.**

Ownership is enforced at two levels:
1. **Route-level** — `@require_ownership()` decorator on endpoints
2. **Data-layer** — `verify_client_ownership()` function for programmatic checks

---

## Enforcement Mechanisms

### 1. `@require_ownership(resource_type, id_field, owner_field)` Decorator

**Location:** `app/utils/permission_helper.py` (re-exported via `app/middleware/permission_middleware.py`)

Intercepts requests before the route handler executes:
1. Extracts the resource ID from URL parameters via `id_field`
2. Queries the `resource_type` collection for the document
3. Compares `doc[owner_field]` against `g.user_id`
4. Returns `403 Forbidden` if ownership check fails
5. **Bypass:** Users with `super_admin` or `ops_lead` roles skip the ownership check

```python
@app.route("/api/projects/<project_id>", methods=["GET"])
@require_ownership("projects", id_field="project_id", owner_field="owner_id")
def get_project(project_id):
    ...
```

### 2. `verify_client_ownership(user_id, resource_type, resource_id)` Function

**Location:** `app/utils/permission_helper.py`

Programmatic ownership verification for use within service logic:
1. Checks if user has admin roles (`super_admin`, `ops_lead`) — returns `True` immediately
2. Queries the collection for the document
3. Compares `doc["owner_id"]` against the provided `user_id`

```python
if not verify_client_ownership(g.user_id, "invoices", invoice_id):
    return forbidden(message="Access denied")
```

---

## Route Coverage Matrix

The following matrix defines which resources require ownership enforcement and the decoration status.

### Client-Facing Resources

| Domain | Resource Type | Route Pattern | Decorator | Owner Field | Status |
|--------|--------------|---------------|-----------|-------------|--------|
| Dashboard | `dashboards` | `GET /api/dashboard/<id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Projects | `projects` | `GET /api/projects/<project_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Projects | `projects` | `PUT /api/projects/<project_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Projects | `projects` | `DELETE /api/projects/<project_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Invoices | `invoices` | `GET /api/invoices/<invoice_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Invoices | `invoices` | `PUT /api/invoices/<invoice_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Invoices | `invoices` | `DELETE /api/invoices/<invoice_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Files | `files` | `GET /api/files/<file_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Files | `files` | `DELETE /api/files/<file_id>` | `@require_ownership` | `owner_id` | ✅ Required |
| Messages | `messages` | `GET /api/messages/<thread_id>` | `@require_ownership` | `owner_id` | ✅ Required |

### List Endpoints (Query-Level Filtering)

For collection endpoints (`GET /api/projects`, `GET /api/invoices`, etc.), ownership is enforced at the **query level** by filtering on `owner_id = g.user_id` in the database query. Admin roles see all records.

| Domain | Route Pattern | Enforcement | Status |
|--------|---------------|-------------|--------|
| Projects | `GET /api/projects` | Query filter: `owner_id` | ✅ Required |
| Invoices | `GET /api/invoices` | Query filter: `owner_id` | ✅ Required |
| Files | `GET /api/files` | Query filter: `owner_id` | ✅ Required |
| Messages | `GET /api/messages` | Query filter: `owner_id` | ✅ Required |

---

## Role Bypass Rules

| Role | Ownership Check | Rationale |
|------|----------------|-----------|
| `super_admin` | ⏭️ Bypassed | Full system access |
| `ops_lead` | ⏭️ Bypassed | Operational oversight |
| `project_manager` | ✅ Enforced | Can only access assigned projects |
| `client` | ✅ Enforced | Can only access own resources |

---

## Multi-Tenant Isolation Rules

### Database Layer
- Every client-facing document MUST contain an `owner_id` field
- Queries for client-role users MUST include `owner_id` filter
- Aggregation pipelines MUST respect ownership boundaries

### API Layer
- All single-resource endpoints MUST use `@require_ownership` or equivalent
- All list endpoints MUST apply query-level ownership filtering
- Cross-resource references (e.g., project → invoices) MUST validate ownership chain

### Session Layer
- JWT tokens contain `user_id` (as `sub` claim) used for ownership resolution
- Token `role` claim determines bypass eligibility
- No cross-session data leakage between portal boundaries

---

## Verification Checklist

- [ ] All single-resource GET endpoints have `@require_ownership` or `verify_client_ownership()`
- [ ] All single-resource PUT/DELETE endpoints have `@require_ownership`
- [ ] All list endpoints filter by `owner_id` for non-admin roles
- [ ] No direct database queries bypass ownership in client-facing code paths
- [ ] Integration/webhook endpoints validate portal identity, not user ownership
