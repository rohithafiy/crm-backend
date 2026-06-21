# Portal 5 — Pipeline & Communications API Contract

---

## Pipeline Endpoints

### PUT /api/portal5/pipeline/:lead_id
**Move Lead to New Stage**

```json
{ "status": "qualified" }
```

**Allowed Transitions**

```
new           → contacted, lost
contacted     → qualified, lost
qualified     → proposal_sent, lost
proposal_sent → negotiation, lost
negotiation   → won, lost
won           → (terminal — no further moves)
lost          → (terminal — no further moves)
```

**Success — 200:** Returns updated lead.

**Error — 400 (invalid transition)**
```json
{
  "success": false,
  "message": "Cannot transition from 'new' to 'won'. Allowed next stages: ['contacted', 'lost']."
}
```

---

### GET /api/portal5/pipeline
**Get Full Pipeline Board**

Returns all non-deleted leads grouped by stage.

**Success — 200**
```json
{
  "success": true,
  "message": "Pipeline board fetched successfully.",
  "data": {
    "new": [ { "id": "...", "full_name": "...", "status": "new" } ],
    "contacted": [],
    "qualified": [ { "id": "...", "full_name": "...", "status": "qualified" } ],
    "proposal_sent": [],
    "negotiation": [],
    "won": [],
    "lost": []
  }
}
```

---

## Communication Endpoints

**Base URL:** `/api/portal5/communications`

### POST /api/portal5/communications
**Log a Communication Entry**

```json
{
  "type": "meeting",
  "client_id": "6678def...",
  "lead_id": null,
  "subject": "Kickoff Call",
  "content": "Discussed project scope and timeline. Client confirmed budget.",
  "attendees": ["Arjun Mehta", "Priya Singh"],
  "action_items": ["Send proposal by Friday", "Share NDA"],
  "file_urls": ["https://cdn.example.com/meeting-notes.pdf"]
}
```

**Required:** `type`, `content`; at least one of `client_id` or `lead_id`

**Type Enum:** `note` | `email` | `meeting` | `file`

**Success — 201:** Returns created communication entry.

---

## Communication Object Shape

```json
{
  "id": "6679abc...",
  "client_id": "6678def...",
  "lead_id": null,
  "type": "meeting",
  "subject": "Kickoff Call",
  "content": "Discussed project scope...",
  "attendees": ["Arjun Mehta", "Priya Singh"],
  "action_items": ["Send proposal by Friday"],
  "file_urls": ["https://cdn.example.com/notes.pdf"],
  "created_by": "user_id_xyz",
  "created_at": "2025-06-15T10:30:00.000Z"
}
```

---

## Standard Error Response Shape

```json
{
  "success": false,
  "message": "Human-readable error description.",
  "errors": ["Optional array of field-level errors"]
}
```

## HTTP Status Codes Used

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success                              |
| 201  | Resource created                     |
| 400  | Validation error / bad request       |
| 401  | Missing or invalid JWT               |
| 403  | Insufficient role permissions        |
| 404  | Resource not found                   |
| 409  | Conflict (duplicate record)          |
| 500  | Internal server error                |
