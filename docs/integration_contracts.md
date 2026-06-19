# Portal 5 Integration Contracts

## Master Integration Rule

**Portal 5 must NEVER directly access Portal 1-4 or Portal 6-8 databases.
All cross-portal data access must go through the respective portal's API endpoints.**

Communication is strictly HTTP-based with HMAC-signed payloads.

---

## Common Protocol

### Authentication
All outbound API calls include:
- `X-Portal-5-Auth`: Portal 5 API key (per-portal, configured in env)
- `X-Portal-Name: portal5`
- `X-Request-Timestamp`: ISO 8601 UTC timestamp
- `X-Webhook-Signature`: HMAC-SHA256 of request body (signed with `PORTAL_WEBHOOK_SECRET`)

### Retry Policy
| Attempt | Delay |
|---------|-------|
| 1 | 0s |
| 2 | 2s |
| 3 | 8s |

After 3 failed attempts, the error is logged and surfaced to the caller.

---

## Portal 1 — Project Request Integration

### Endpoints (Portal 5 → Portal 1)

#### Sync Project Request
`POST /api/project-requests`
```json
{
  "source": "portal5",
  "type": "project_request.sync",
  "data": {
    "external_id": "665a...",
    "title": "Q4 Marketing Campaign",
    "requester": "client@example.com",
    "description": "Full-stack marketing portal",
    "priority": "high",
    "source_system": "portal5-crm"
  }
}
```

#### Create Lead
`POST /api/leads`
```json
{
  "source": "portal5",
  "type": "lead.created",
  "data": {
    "lead_id": "665a...",
    "name": "Acme Corp",
    "email": "contact@acme.com",
    "phone": "+1234567890",
    "source": "crm-portal5"
  }
}
```

#### Track Request
`GET /api/project-requests/{request_id}/track`
Returns tracking status.

### Responsibilities
| Responsibility | Portal 5 Action | Portal 1 Endpoint |
|---|---|---|
| Request synchronization | `portal1_sync_request()` | `POST /api/project-requests` |
| Lead creation triggers | `portal1_create_lead()` | `POST /api/leads` |
| Request tracking | `portal1_track_request()` | `GET /api/project-requests/{id}/track` |
| Data mapping | `_map_project_request()` | Transforms CRM fields → Portal 1 format |

---

## Portal 3 — Workspace Integration

### Endpoints (Portal 5 → Portal 3)

#### Create Workspace
`POST /api/workspaces`
```json
{
  "source": "portal5",
  "type": "workspace.create",
  "data": {
    "client_id": "665a...",
    "client_name": "Acme Corp",
    "client_email": "contact@acme.com",
    "company": "Acme Inc.",
    "owner_id": "665b..."
  }
}
```

#### Associate Project
`POST /api/projects`
```json
{
  "source": "portal5",
  "type": "project.associate",
  "data": {
    "proposal_id": "665c...",
    "client_id": "665a...",
    "title": "Website Redesign",
    "amount": 25000.00,
    "status": "approved"
  }
}
```

#### Sync Progress
`PUT /api/progress`
```json
{
  "source": "portal5",
  "type": "progress.sync",
  "data": {
    "project_id": "665c...",
    "progress_pct": 75,
    "status": "in_progress",
    "updated_at": "2026-06-18T12:00:00Z"
  }
}
```

### Responsibilities
| Responsibility | Portal 5 Action | Portal 3 Endpoint |
|---|---|---|
| Client workspace creation | `portal3_create_workspace()` | `POST /api/workspaces` |
| Project association | `portal3_associate_project()` | `POST /api/projects` |
| Progress synchronization | `portal3_sync_progress()` | `PUT /api/progress` |

---

## Portal 8 — Automation Integration

### Endpoints (Portal 5 → Portal 8)

#### Trigger Workflow
`POST /api/workflows/trigger`
```json
{
  "source": "portal5",
  "type": "workflow.trigger",
  "data": {
    "event": "lead.assigned",
    "context": {
      "lead_id": "665a...",
      "assignee_id": "665b...",
      "previous_owner": null
    },
    "timestamp": "2026-06-18T12:00:00Z"
  }
}
```

#### Send Notification
`POST /api/notifications`
```json
{
  "source": "portal5",
  "type": "notification.send",
  "data": {
    "recipient": "user@example.com",
    "channel": "email",
    "template": "lead_assigned",
    "variables": { "lead_name": "Acme Corp" }
  }
}
```

#### Emit CRM Event
`POST /api/events`
```json
{
  "source": "portal5",
  "type": "crm.event",
  "data": {
    "event": "proposal.approved",
    "payload": {
      "proposal_id": "665c...",
      "client_id": "665a...",
      "amount": 25000
    },
    "timestamp": "2026-06-18T12:00:00Z"
  }
}
```

#### Sync Activity
`POST /api/activities`
```json
{
  "source": "portal5",
  "type": "activity.sync",
  "data": {
    "user_id": "665b...",
    "action": "lead.status_changed",
    "resource": "lead",
    "resource_id": "665a...",
    "metadata": { "from": "new", "to": "contacted" },
    "timestamp": "2026-06-18T12:00:00Z"
  }
}
```

### Responsibilities
| Responsibility | Portal 5 Action | Portal 8 Endpoint |
|---|---|---|
| Workflow triggers | `portal8_trigger_workflow()` | `POST /api/workflows/trigger` |
| Notification events | `portal8_send_notification()` | `POST /api/notifications` |
| CRM automation events | `portal8_emit_crm_event()` | `POST /api/events` |
| Activity synchronization | `portal8_sync_activity()` | `POST /api/activities` |

---

## Portal 6 — Performance Integration

### Endpoints (Portal 5 → Portal 6)

#### Push Metrics
`POST /api/metrics`
```json
{
  "source": "portal5",
  "type": "delivery.metrics",
  "data": {
    "project_id": "665c...",
    "client_id": "665a...",
    "milestones_completed": 8,
    "milestones_total": 10,
    "on_track": true,
    "delivery_date": "2026-07-15",
    "budget_utilization_pct": 85.5
  }
}
```

#### Track Completion
`PUT /api/projects/{project_id}/complete`
```json
{
  "source": "portal5",
  "type": "project.completed",
  "data": {
    "project_id": "665c...",
    "completed_at": "2026-07-15T18:00:00Z",
    "source_system": "portal5-crm"
  }
}
```

#### Push Score
`POST /api/scores`
```json
{
  "source": "portal5",
  "type": "performance.score",
  "data": {
    "client_id": "665a...",
    "project_id": "665c...",
    "score_type": "delivery",
    "score_value": 92.5,
    "period": "2026-Q2",
    "dimensions": {
      "timeliness": 95,
      "quality": 90,
      "communication": 88
    }
  }
}
```

### Responsibilities
| Responsibility | Portal 5 Action | Portal 6 Endpoint |
|---|---|---|
| Push delivery metrics | `portal6_push_metrics()` | `POST /api/metrics` |
| Project completion tracking | `portal6_track_completion()` | `PUT /api/projects/{id}/complete` |
| Performance scoring | `portal6_push_score()` | `POST /api/scores` |

---

## Incoming Webhooks (Portal → Portal 5)

### Endpoint
`POST /integration/webhook`

### Headers
- `X-Portal-Name`: portal identifier (`portal1`, `portal3`, `portal6`, `portal8`)
- `X-Webhook-Signature`: HMAC-SHA256 of request body

### Supported Events
| Portal | Event | Payload |
|---|---|---|
| Portal 1 | `project.request.created` | `{ "request_id", "title", "status" }` |
| Portal 1 | `project.request.updated` | `{ "request_id", "changes" }` |
| Portal 3 | `workspace.created` | `{ "workspace_id", "client_id", "url" }` |
| Portal 3 | `progress.updated` | `{ "project_id", "progress_pct" }` |
| Portal 8 | `workflow.completed` | `{ "workflow_id", "status", "output" }` |
| Portal 8 | `notification.delivered` | `{ "notification_id", "status" }` |
| Portal 6 | `metrics.requested` | `{ "project_id", "metrics" }` |
| Portal 6 | `score.updated` | `{ "client_id", "score_type", "value" }` |

Event handlers are registered via `register_event_handler(event_type, handler_fn)`.
