# Portal 6 Integration Contract — Performance & Scoring

## Overview

This document defines the integration contract between **Portal 5 (CRM)** and **Portal 6 (Performance & Analytics)**.
Portal 5 pushes delivery metrics, project completion data, and performance scores to Portal 6 for downstream reporting and scoring matrix configurations.

All communication follows the shared cross-portal HTTP protocol with HMAC-signed payloads.

---

## Integration Protocol

### Authentication Headers
All Portal 5 → Portal 6 API calls include:

| Header | Value |
|--------|-------|
| `X-Portal-5-Auth` | Portal 5 API key for Portal 6 |
| `X-Portal-Name` | `portal5` |
| `X-Request-Timestamp` | ISO 8601 UTC timestamp |
| `X-Webhook-Signature` | HMAC-SHA256 of request body |

### Retry Policy

| Attempt | Delay |
|---------|-------|
| 1 | 0s |
| 2 | 2s |
| 3 | 8s |

After 3 failed attempts, the error is logged and surfaced to the caller.

---

## Performance Metrics

### Push Delivery Metrics
**Endpoint:** `POST /api/metrics`
**Portal 5 Function:** `portal6_push_metrics()`

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

#### Data Schema — `delivery.metrics`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | `string` | ✅ | Portal 5 project identifier |
| `client_id` | `string` | ✅ | Associated client identifier |
| `milestones_completed` | `integer` | ✅ | Completed milestones count |
| `milestones_total` | `integer` | ✅ | Total milestones in project |
| `on_track` | `boolean` | ✅ | Whether delivery is on schedule |
| `delivery_date` | `string (date)` | ✅ | Expected delivery date (ISO 8601) |
| `budget_utilization_pct` | `float` | ✅ | Budget utilization percentage (0-100) |

---

## Project Completion Metrics

### Track Project Completion
**Endpoint:** `PUT /api/projects/{project_id}/complete`
**Portal 5 Function:** `portal6_track_completion()`

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

#### Data Schema — `project.completed`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | `string` | ✅ | Portal 5 project identifier |
| `completed_at` | `string (datetime)` | ✅ | Completion timestamp (ISO 8601 UTC) |
| `source_system` | `string` | ✅ | Originating system identifier |

---

## Delivery Metrics

Portal 6 may request delivery metrics from Portal 5 via incoming webhook.

### Inbound Event: `metrics.requested`
**Portal 5 Endpoint:** `POST /integration/webhook`

```json
{
  "event": "metrics.requested",
  "portal": "portal6",
  "data": {
    "project_id": "665c...",
    "metrics": ["milestones", "budget", "timeline"]
  }
}
```

Portal 5 responds by pushing the requested metrics back to Portal 6 via `portal6_push_metrics()`.

#### Request Schema — `metrics.requested`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_id` | `string` | ✅ | Project to retrieve metrics for |
| `metrics` | `array[string]` | ✅ | Requested metric categories |

Supported metric categories: `milestones`, `budget`, `timeline`, `quality`, `resources`

---

## Scoring Payloads

### Push Performance Score
**Endpoint:** `POST /api/scores`
**Portal 5 Function:** `portal6_push_score()`

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

#### Data Schema — `performance.score`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `client_id` | `string` | ✅ | Client identifier |
| `project_id` | `string` | ✅ | Project identifier |
| `score_type` | `string` | ✅ | Score category (see below) |
| `score_value` | `float` | ✅ | Aggregate score (0-100) |
| `period` | `string` | ✅ | Reporting period (e.g. `"2026-Q2"`) |
| `dimensions` | `object` | ✅ | Breakdown scores per dimension |

#### Score Types

| Score Type | Description |
|------------|-------------|
| `delivery` | Overall delivery performance |
| `quality` | Code/output quality assessment |
| `timeliness` | On-time delivery rating |
| `communication` | Client communication rating |
| `budget` | Budget adherence rating |

#### Dimension Fields

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `timeliness` | `integer` | 0-100 | On-time delivery score |
| `quality` | `integer` | 0-100 | Output quality score |
| `communication` | `integer` | 0-100 | Responsiveness and clarity |
| `budget_adherence` | `integer` | 0-100 | Budget management score |
| `scope_management` | `integer` | 0-100 | Scope control score |

### Inbound Event: `score.updated`
**Portal 5 Endpoint:** `POST /integration/webhook`

Portal 6 notifies Portal 5 when scores are recalculated:

```json
{
  "event": "score.updated",
  "portal": "portal6",
  "data": {
    "client_id": "665a...",
    "score_type": "delivery",
    "value": 94.0
  }
}
```

---

## Core API Contract Schemas

### Endpoint Summary

| Direction | Method | Endpoint | Event Type | Portal 5 Function |
|-----------|--------|----------|------------|-------------------|
| Outbound | `POST` | `/api/metrics` | `delivery.metrics` | `portal6_push_metrics()` |
| Outbound | `PUT` | `/api/projects/{id}/complete` | `project.completed` | `portal6_track_completion()` |
| Outbound | `POST` | `/api/scores` | `performance.score` | `portal6_push_score()` |
| Inbound | `POST` | `/integration/webhook` | `metrics.requested` | Event handler |
| Inbound | `POST` | `/integration/webhook` | `score.updated` | Event handler |

### Standard Response Envelope

Portal 6 returns responses in the shared envelope format:

```json
{
  "status": "success",
  "code": 200,
  "data": { ... },
  "message": "Metrics received",
  "metadata": {
    "timestamp": "2026-06-18T12:00:00.000000+00:00"
  }
}
```

### Error Codes

| HTTP | Code | Description |
|------|------|-------------|
| 400 | `INVALID_PAYLOAD` | Malformed or missing required fields |
| 401 | `AUTH_ERROR` | Invalid or missing authentication headers |
| 404 | `PROJECT_NOT_FOUND` | Referenced project does not exist |
| 409 | `DUPLICATE_ENTRY` | Metric or score already submitted for period |
| 429 | `RATE_LIMIT` | Too many requests |
| 500 | `INTERNAL_ERROR` | Portal 6 internal failure |

---

## Implementation Reference

Portal 5 integration functions are implemented in:
- **HTTP Client:** `app/utils/integration_helper.py` → `call_portal_api(PortalID.PORTAL_6, ...)`
- **Integration Service:** `app/services/integration_service.py`
- **Event Handlers:** Registered via `register_event_handler(event_type, handler_fn)`
- **Portal Config:** `PORTAL6_BASE_URL` and `PORTAL6_API_KEY` in environment variables
