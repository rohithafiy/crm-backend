# Portal 5 — Database Documentation

**Database:** MongoDB (Atlas / local)  
**Database Name:** `lti_hub`  

---

## Collections

### 1. `p5_leads`

**Description:** Lead records tracking potential clients through the sales pipeline.

**Schema Fields**

| Field               | Type          | Description                                        |
|---------------------|---------------|----------------------------------------------------|
| `_id`               | ObjectId      | Primary key                                        |
| `full_name`         | string        | Lead's full name                                   |
| `company_name`      | string        | Company name                                       |
| `email`             | string        | Email address (unique, sparse)                     |
| `phone`             | string        | Raw phone number                                   |
| `phone_normalized`  | string        | Normalized phone (unique, sparse)                  |
| `industry`          | string        | Industry sector                                    |
| `service_type`      | string        | Service category                                   |
| `project_description`| string       | Project overview                                   |
| `budget_range`      | string        | Budget range description                           |
| `timeline`          | string        | Expected timeline                                  |
| `estimated_value`   | number        | Estimated monetary value                           |
| `source`            | string        | Acquisition source                                 |
| `portal1_request_id`| string        | External reference (sparse)                        |
| `status`            | string        | Pipeline stage: `new`, `contacted`, `qualified`, `proposal_sent`, `negotiation`, `won`, `lost` |
| `assigned_to`       | string        | Assigned user ID                                   |
| `follow_up_date`    | datetime      | Scheduled follow-up timestamp                      |
| `notes`             | string        | Internal notes                                     |
| `file_urls`         | array[string] | Attached file URLs                                 |
| `assignment_history`| array         | History of assignments                             |
| `audit_logs`        | array         | Audit trail of changes                             |
| `created_by`        | string        | Creator user ID                                    |
| `created_at`        | datetime      | Document creation timestamp                        |
| `updated_at`        | datetime      | Last update timestamp                              |
| `is_deleted`        | boolean       | Soft-delete flag                                   |
| `deleted_at`        | datetime|null | Soft-delete timestamp                              |

**Indexes**

| Index Name                     | Fields                           | Unique | Sparse |
|--------------------------------|----------------------------------|--------|--------|
| `idx_leads_email_unique`       | `email` ASC                      | Yes    | Yes    |
| `idx_leads_email`              | `email` ASC                      | No     | No     |
| `idx_leads_company_name`       | `company_name` ASC               | No     | No     |
| `idx_leads_status`             | `status` ASC                     | No     | No     |
| `idx_leads_assigned_to`        | `assigned_to` ASC                | No     | No     |
| `idx_leads_follow_up_date`     | `follow_up_date` ASC             | No     | No     |
| `idx_leads_created_at`         | `created_at` DESC                | No     | No     |
| `idx_leads_status_assigned`    | `status` ASC, `assigned_to` ASC  | No     | No     |
| `idx_leads_source`             | `source` ASC                     | No     | No     |
| `idx_leads_is_deleted`         | `is_deleted` ASC                 | No     | No     |
| `idx_leads_portal1_ref`        | `portal1_request_id` ASC         | No     | Yes    |
| `idx_leads_text_search`        | `full_name` TEXT, `company_name` TEXT, `email` TEXT | No | No |
| `idx_leads_phone_normalized`   | `phone_normalized` ASC           | Yes    | Yes    |

---

### 2. `p5_clients`

**Description:** Client records for won/converted opportunities.

**Schema Fields**

| Field               | Type          | Description                                        |
|---------------------|---------------|----------------------------------------------------|
| `_id`               | ObjectId      | Primary key                                        |
| `user_id`           | string        | Associated user ID                                 |
| `company_name`      | string        | Company name                                       |
| `client_name`       | string        | Primary contact name                               |
| `contact_person`    | string        | Contact person name                                |
| `company_logo_url`  | string        | Logo URL                                           |
| `industry`          | string        | Industry sector                                    |
| `email`             | string        | Email address (unique, sparse)                     |
| `phone`             | string        | Raw phone number                                   |
| `phone_normalized`  | string        | Normalized phone (unique, sparse)                  |
| `address`           | string/object | Address details                                    |
| `website`           | string        | Company website                                    |
| `gst_number`        | string        | GST/VAT number                                     |
| `lead_id`           | ObjectId      | Source lead reference (sparse)                     |
| `status`            | string        | Status: `active`, `inactive`, `churned`            |
| `total_revenue`     | number        | Cumulative revenue                                 |
| `total_projects`    | number        | Project count                                      |
| `created_by`        | string        | Creator user ID                                    |
| `created_at`        | datetime      | Document creation timestamp                        |
| `updated_at`        | datetime      | Last update timestamp                              |
| `is_deleted`        | boolean       | Soft-delete flag                                   |
| `deleted_at`        | datetime|null | Soft-delete timestamp                              |

**Indexes**

| Index Name                       | Fields                                         | Unique | Sparse |
|----------------------------------|------------------------------------------------|--------|--------|
| `idx_clients_email_unique`       | `email` ASC                                    | Yes    | Yes    |
| `idx_clients_email`              | `email` ASC                                    | No     | No     |
| `idx_clients_company_name`       | `company_name` ASC                             | No     | No     |
| `idx_clients_status`             | `status` ASC                                   | No     | No     |
| `idx_clients_assigned_to`        | `assigned_to` ASC                              | No     | Yes    |
| `idx_clients_user_id`            | `user_id` ASC                                  | No     | Yes    |
| `idx_clients_follow_up_date`     | `follow_up_date` ASC                           | No     | Yes    |
| `idx_clients_created_at`         | `created_at` DESC                              | No     | No     |
| `idx_clients_lead_id`            | `lead_id` ASC                                  | No     | Yes    |
| `idx_clients_industry`           | `industry` ASC                                 | No     | No     |
| `idx_clients_is_deleted`         | `is_deleted` ASC                               | No     | No     |
| `idx_clients_text_search`        | `company_name` TEXT, `contact_person` TEXT, `email` TEXT | No | No |
| `idx_clients_phone_normalized`   | `phone_normalized` ASC                         | Yes    | Yes    |

---

### 3. `p5_communications`

**Description:** Communication history entries linked to clients or leads.

**Schema Fields**

| Field                | Type          | Description                                     |
|----------------------|---------------|-------------------------------------------------|
| `_id`                | ObjectId      | Primary key                                     |
| `client_id`          | ObjectId      | Linked client (optional if lead_id provided)    |
| `lead_id`            | ObjectId      | Linked lead (optional if client_id provided)    |
| `communication_type` | string        | Type: `note`, `email`, `call`, `meeting`, `file`|
| `subject`            | string        | Subject line                                    |
| `content`            | string        | Communication body/content                      |
| `attendees`          | array[string] | Attendee names                                  |
| `action_items`       | array[string] | Action items                                    |
| `file_urls`          | array[string] | Attached file URLs                              |
| `created_by`         | string        | Creator user ID                                 |
| `created_at`         | datetime      | Document creation timestamp                     |

**Indexes**

| Index Name                     | Fields                                | Unique | Sparse |
|--------------------------------|---------------------------------------|--------|--------|
| `idx_comms_client_timeline`    | `client_id` ASC, `created_at` DESC    | No     | No     |
| `idx_comms_lead_timeline`      | `lead_id` ASC, `created_at` DESC      | No     | No     |
| `idx_comms_communication_type` | `communication_type` ASC              | No     | No     |
| `idx_comms_created_by`         | `created_by` ASC                      | No     | No     |

---

### 4. `p5_activity_logs`

**Description:** Aggregated activity feed entries for dashboard/recent-activity display.

**Schema Fields**

| Field           | Type     | Description                        |
|-----------------|----------|------------------------------------|
| `_id`           | ObjectId | Primary key                        |
| `action`        | string   | Action identifier                  |
| `performed_by`  | string   | User who performed the action      |
| `details`       | string   | Human-readable description         |
| `resource_type` | string   | Resource type (lead, client, etc.) |
| `resource_id`   | string   | Related resource ID                |
| `timestamp`     | datetime | When the action occurred           |

**Indexes**

| Index Name         | Fields             | Unique | Sparse |
|--------------------|--------------------|--------|--------|
| `idx_activity_ts`  | `timestamp` DESC   | No     | No     |

---

## Relationships

```
p5_leads ──→ p5_clients
    ↑             ↑
    │             │
    └── p5_communications  (via client_id / lead_id)
         │
         └── p5_activity_logs
```

- A **Lead** can be converted to a **Client** (lead_id stored on client).
- **Communications** are linked to either a **Lead** or a **Client**.
- **Activity Logs** track key events across all resource types for the feed.
