# Portal 5 — Lead API Contract

**Base URL:** `/api/portal5/leads`  
**Auth:** All endpoints require `Authorization: Bearer <JWT>` header.  
**Allowed Roles:** `super_admin`, `ops_lead`, `project_manager`

---

## POST /api/portal5/leads
### Create Lead

**Request Body**
```json
{
  "full_name": "Arjun Mehta",
  "email": "arjun.mehta@acme.in",
  "phone": "+919876543210",
  "source": "website",
  "company_name": "Acme Corp",
  "industry": "Technology",
  "service_type": "Web Development",
  "project_description": "E-commerce platform rebuild",
  "budget_range": "5L-10L",
  "timeline": "Q3 2025",
  "estimated_value": 750000,
  "portal1_request_id": "p1_req_abc123",
  "assigned_to": "user_id_xyz",
  "follow_up_date": "2025-07-01T10:00:00Z",
  "notes": "High priority referral",
  "file_urls": ["https://cdn.example.com/brief.pdf"]
}
```

**Required Fields:** `full_name`, `email`, `phone`, `source`

**Source Enum:** `website` | `referral` | `portal1` | `social` | `email` | `cold_call` | `event` | `other`

**Success Response — 201**
```json
{
  "success": true,
  "message": "Lead created successfully.",
  "data": {
    "id": "6678abc...",
    "full_name": "Arjun Mehta",
    "email": "arjun.mehta@acme.in",
    "status": "new",
    "created_at": "2025-06-15T08:30:00.000Z"
  }
}
```

**Error — 400 Validation**
```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": ["'email' is required and cannot be empty."]
}
```

**Error — 409 Duplicate**
```json
{
  "success": false,
  "message": "A lead with email 'arjun.mehta@acme.in' already exists (id: 6678abc...)."
}
```

---

## GET /api/portal5/leads
### List Leads

**Query Parameters**

| Param       | Type   | Description                                         |
|-------------|--------|-----------------------------------------------------|
| page        | int    | Page number (default: 1)                            |
| limit       | int    | Per page, max 100 (default: 20)                     |
| status      | string | Filter: `new` \| `contacted` \| `qualified` \| ... |
| assigned_to | string | Filter by user ID                                   |
| source      | string | Filter by source                                    |
| search      | string | Regex search on full_name, company_name, email      |

**Success Response — 200**
```json
{
  "success": true,
  "message": "Leads fetched successfully.",
  "data": [ { "id": "...", "full_name": "..." } ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total_records": 100,
    "total_pages": 5
  }
}
```

---

## GET /api/portal5/leads/:id
### Get Single Lead

**Success — 200:** Returns full lead object.  
**Error — 404:** `"Lead not found."`  
**Error — 400:** `"'abc' is not a valid lead ID."`

---

## PUT /api/portal5/leads/:id
### Update Lead (Partial)

Send only the fields to update. Protected fields (`_id`, `created_at`, `created_by`) are ignored even if sent.

**Success — 200:** Returns updated lead object.

---

## DELETE /api/portal5/leads/:id
### Soft-Delete Lead

Sets `is_deleted: true` and `deleted_at: <timestamp>`. Record is never removed from DB.

**Success — 200**
```json
{ "success": true, "message": "Lead deleted successfully.", "data": null }
```

---

## POST /api/portal5/leads/:id/assign
### Assign Lead

```json
{
  "assigned_to": "user_id_abc",
  "note": "Assigning to Priya for Q3 follow-up"
}
```

Appends to `assignment_history` array with `{ assigned_to, assigned_by, note, assigned_at }`.

**Success — 200:** Returns updated lead.

---

## POST /api/portal5/leads/:id/convert
### Convert Lead to Client

**Rules:**
- Lead must exist and not be deleted
- Lead `status` must be `"qualified"`
- Creates a new `p5_clients` document
- Sets lead `status` to `"won"`

**Success — 201**
```json
{
  "success": true,
  "message": "Lead converted to client successfully.",
  "data": {
    "lead": { "id": "...", "status": "won" },
    "client": { "id": "...", "company_name": "Acme Corp" }
  }
}
```

**Error — 400**
```json
{
  "success": false,
  "message": "Lead must be in 'qualified' status to convert. Current status: 'new'."
}
```

---

## Status Enum

| Value          | Description                         |
|----------------|-------------------------------------|
| `new`          | Freshly created                     |
| `contacted`    | Initial outreach made               |
| `qualified`    | Lead confirmed as viable            |
| `proposal_sent`| Proposal/quote delivered            |
| `negotiation`  | Active commercial discussion        |
| `won`          | Converted to client                 |
| `lost`         | Lead dropped / not converted        |
