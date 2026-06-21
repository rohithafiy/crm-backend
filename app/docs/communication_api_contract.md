# Portal 5 — Communication API Contract

**Base URL:** `/api/portal5`  
**Auth:** All endpoints require `Authorization: Bearer <JWT>` header.  
**Allowed Roles:** `super_admin`, `ops_lead`, `project_manager`

---

## GET /api/portal5/clients/:clientId/communications
### List Communications for a Client

**Query Parameters**

| Param | Type   | Description                                      |
|-------|--------|--------------------------------------------------|
| type  | string | Filter: `note` \| `email` \| `meeting` \| `file` |
| order | string | Sort: `asc` (oldest first) or `desc` (default)   |

**Success Response — 200**
```json
{
  "success": true,
  "message": "Communications fetched successfully.",
  "data": [
    {
      "id": "6681abc...",
      "client_id": "6678def...",
      "communication_type": "meeting",
      "subject": "Kickoff Call",
      "content": "Discussed project scope. Client confirmed budget of 7.5L.",
      "attendees": ["Arjun Mehta", "Priya Singh"],
      "action_items": ["Send proposal by Friday", "Share NDA"],
      "file_urls": [],
      "created_by": "user_001",
      "created_at": "2025-06-20T14:30:00.000Z"
    }
  ]
}
```

**Error — 400**
```json
{
  "success": false,
  "message": "'abc' is not a valid client ID."
}
```

---

## POST /api/portal5/clients/:clientId/communications
### Add a Communication for a Client

**Request Body**
```json
{
  "communication_type": "meeting",
  "subject": "Kickoff Call",
  "content": "Discussed project scope.",
  "attendees": ["Arjun Mehta", "Priya Singh"],
  "action_items": ["Send proposal by Friday"],
  "file_urls": []
}
```

**Communication Type Enum:** `note` | `email` | `call` | `meeting` | `file`

**Required Fields:** `communication_type`, `content`

**Success Response — 201**
```json
{
  "success": true,
  "message": "Communication logged successfully.",
  "data": {
    "id": "6681abc...",
    "client_id": "6678def...",
    "communication_type": "meeting",
    "subject": "Kickoff Call",
    "content": "Discussed project scope.",
    "created_at": "2025-06-20T14:30:00.000Z"
  }
}
```

**Error — 400 Validation**
```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": ["'communication_type' is required."]
}
```

**Error — 403 Forbidden**
```json
{
  "success": false,
  "message": "Insufficient permissions for this resource"
}
```

---

## DELETE /api/portal5/communications/:id
### Delete a Communication

Hard-deletes a communication record.

**Success — 200**
```json
{
  "success": true,
  "message": "Communication deleted successfully.",
  "data": null
}
```

**Error — 403 Forbidden**
```json
{
  "success": false,
  "message": "Insufficient permissions for this resource"
}
```

**Error — 404**
```json
{
  "success": false,
  "message": "Communication not found."
}
```
