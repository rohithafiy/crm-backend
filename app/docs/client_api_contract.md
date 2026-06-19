# Portal 5 — Client API Contract

**Base URL:** `/api/portal5/clients`  
**Auth:** All endpoints require `Authorization: Bearer <JWT>` header.  
**Allowed Roles:** `super_admin`, `ops_lead`, `project_manager`

---

## POST /api/portal5/clients
### Create Client

```json
{
  "company_name": "Acme Corp Pvt Ltd",
  "contact_person": "Arjun Mehta",
  "email": "arjun@acme.in",
  "phone": "+919876543210",
  "company_logo_url": "https://cdn.example.com/logo.png",
  "industry": "Technology",
  "address": {
    "street": "42 MG Road",
    "city": "Bengaluru",
    "state": "Karnataka",
    "country": "India",
    "pincode": "560001"
  },
  "website": "https://acme.in",
  "gst_number": "29ABCDE1234F1Z5",
  "lead_id": "6678abc..."
}
```

**Required:** `company_name`, `contact_person`, `email`, `phone`

**Success — 201:** Returns created client object.  
**Error — 409:** Duplicate email.

---

## GET /api/portal5/clients
### List Clients

| Param    | Type   | Description                              |
|----------|--------|------------------------------------------|
| page     | int    | Default: 1                               |
| limit    | int    | Default: 20, max: 100                    |
| status   | string | `active` \| `inactive` \| `churned`      |
| industry | string | Partial match (case-insensitive)         |
| search   | string | Searches company_name, contact_person, email |

**Success — 200** with pagination envelope.

---

## GET /api/portal5/clients/:id
## PUT /api/portal5/clients/:id
## DELETE /api/portal5/clients/:id

Standard CRUD. DELETE is soft-delete only.

**Status Enum:** `active` | `inactive` | `churned`

---

## Client Object Shape

```json
{
  "id": "6678def...",
  "user_id": null,
  "company_name": "Acme Corp Pvt Ltd",
  "company_logo_url": "https://...",
  "industry": "Technology",
  "contact_person": "Arjun Mehta",
  "email": "arjun@acme.in",
  "phone": "+919876543210",
  "address": {
    "street": "42 MG Road",
    "city": "Bengaluru",
    "state": "Karnataka",
    "country": "India",
    "pincode": "560001"
  },
  "website": "https://acme.in",
  "gst_number": "29ABCDE1234F1Z5",
  "lead_id": "6678abc...",
  "status": "active",
  "total_revenue": 0.0,
  "total_projects": 0,
  "created_by": "user_id_xyz",
  "created_at": "2025-06-15T08:30:00.000Z",
  "updated_at": "2025-06-15T08:30:00.000Z"
}
```
