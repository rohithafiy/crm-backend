# RBAC Matrix — Role-Based Access Control

## Overview

This document defines the complete role-to-permission mapping for Portal 5 (CRM).
All access control decisions reference this matrix as the authoritative specification.

**Implementation:** `app/configs/security_config.py` (role definitions, hierarchy, permissions)
**Enforcement:** `app/middleware/role_middleware.py` and `app/middleware/permission_middleware.py`

---

## Role Definitions

| Role | Description | Scope |
|------|-------------|-------|
| `super_admin` | Full system administrator | Unrestricted access to all resources and settings |
| `ops_lead` | Operations team lead | Full operational access, no system-level settings |
| `project_manager` | Project manager | Manage assigned projects and related resources |
| `client` | External client | View own resources only |

---

## Role Hierarchy

Higher roles inherit all permissions of lower roles:

```
super_admin
  └── ops_lead
       └── project_manager
            └── client
```

| Role | Inherits From |
|------|--------------|
| `super_admin` | `ops_lead`, `project_manager`, `client` |
| `ops_lead` | `project_manager`, `client` |
| `project_manager` | `client` |
| `client` | — |

---

## Permission Matrix

Legend:
- ✅ Full Access
- 📝 Own Resources Only
- 👁️ Read Only (Own)
- ❌ No Access

### CRM Dashboard

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| View global dashboard | ✅ | ✅ | ❌ | ❌ |
| View team dashboard | ✅ | ✅ | ✅ | ❌ |
| View own dashboard | ✅ | ✅ | ✅ | ✅ |
| Export dashboard data | ✅ | ✅ | ❌ | ❌ |

### Leads

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Create lead | ✅ | ✅ | ✅ | ❌ |
| View all leads | ✅ | ✅ | ❌ | ❌ |
| View assigned leads | ✅ | ✅ | ✅ | ❌ |
| Update lead | ✅ | ✅ | 📝 | ❌ |
| Delete lead | ✅ | ✅ | ❌ | ❌ |
| Assign lead | ✅ | ✅ | ❌ | ❌ |
| Convert lead to client | ✅ | ✅ | ✅ | ❌ |

### Clients

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Create client | ✅ | ✅ | ❌ | ❌ |
| View all clients | ✅ | ✅ | ❌ | ❌ |
| View assigned clients | ✅ | ✅ | ✅ | ❌ |
| View own profile | ✅ | ✅ | ✅ | ✅ |
| Update client | ✅ | ✅ | 📝 | ❌ |
| Delete client | ✅ | ❌ | ❌ | ❌ |

### Proposals

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Create proposal | ✅ | ✅ | ✅ | ❌ |
| View all proposals | ✅ | ✅ | ❌ | ❌ |
| View own proposals | ✅ | ✅ | ✅ | 👁️ |
| Update proposal | ✅ | ✅ | 📝 | ❌ |
| Approve proposal | ✅ | ✅ | ❌ | ✅ |
| Delete proposal | ✅ | ✅ | ❌ | ❌ |

### Quotations

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Create quotation | ✅ | ✅ | ✅ | ❌ |
| View all quotations | ✅ | ✅ | ❌ | ❌ |
| View own quotations | ✅ | ✅ | ✅ | 👁️ |
| Update quotation | ✅ | ✅ | 📝 | ❌ |
| Accept quotation | ✅ | ✅ | ❌ | ✅ |
| Delete quotation | ✅ | ✅ | ❌ | ❌ |

### Invoices

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Create invoice | ✅ | ✅ | ✅ | ❌ |
| View all invoices | ✅ | ✅ | ❌ | ❌ |
| View own invoices | ✅ | ✅ | ✅ | 👁️ |
| Update invoice | ✅ | ✅ | 📝 | ❌ |
| Delete invoice | ✅ | ❌ | ❌ | ❌ |
| Mark as paid | ✅ | ✅ | ❌ | ❌ |

### Payments

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Record payment | ✅ | ✅ | ❌ | ❌ |
| View all payments | ✅ | ✅ | ❌ | ❌ |
| View own payments | ✅ | ✅ | ✅ | 👁️ |
| Refund payment | ✅ | ❌ | ❌ | ❌ |

### Analytics

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| View global analytics | ✅ | ✅ | ❌ | ❌ |
| View team analytics | ✅ | ✅ | ✅ | ❌ |
| View own analytics | ✅ | ✅ | ✅ | ✅ |
| Export reports | ✅ | ✅ | ❌ | ❌ |

### Settings

| Action | `super_admin` | `ops_lead` | `project_manager` | `client` |
|--------|:---:|:---:|:---:|:---:|
| Manage users | ✅ | ❌ | ❌ | ❌ |
| Manage roles | ✅ | ❌ | ❌ | ❌ |
| System settings | ✅ | ❌ | ❌ | ❌ |
| Audit logs | ✅ | ❌ | ❌ | ❌ |
| Portal configuration | ✅ | ❌ | ❌ | ❌ |

---

## Named Permissions

These fine-grained permissions are defined in `SecurityConfig.PERMISSIONS` and enforced via `@require_permission()`:

| Permission Key | Allowed Roles | Description |
|----------------|---------------|-------------|
| `admin:users` | `super_admin` | User management (create, deactivate, role assignment) |
| `admin:roles` | `super_admin` | Role definition and hierarchy management |
| `admin:settings` | `super_admin` | System-wide configuration |
| `admin:audit` | `super_admin` | Audit log access and export |

---

## Enforcement Implementation

### Decorator Usage

```python
from app.middleware.role_middleware import require_role, require_roles
from app.middleware.permission_middleware import require_permission, require_ownership

# Single role check
@require_role("super_admin")
def admin_only_action():
    ...

# Multiple roles (any match)
@require_roles(["super_admin", "ops_lead"])
def ops_action():
    ...

# Named permission check
@require_permission("admin:users")
def manage_users():
    ...

# Ownership enforcement
@require_ownership("projects", id_field="project_id")
def get_project(project_id):
    ...
```
