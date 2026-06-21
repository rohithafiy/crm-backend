# Portal 5 — Security Verification Document

This document describes how the security controls implemented in Portal 5 CRM & Client Management are verified.

## 1. Cookie-based Session Hardening Verification

All user authentication tokens are stored in HTTP-Only, Secure, and SameSite=Strict cookies.

### Verification Steps
1. Execute a successful login request via Postman or the test client.
2. Inspect the HTTP response `Set-Cookie` headers.
3. Verify that:
   - `access_token` and `refresh_token` are set.
   - `HttpOnly` attribute is present.
   - `Secure` attribute is present.
   - `SameSite=Strict` is present.
4. Verify that the response body does *not* contain the plain-text token.

## 2. Client Isolation & Ownership Verification

A client must never access resources (Dashboard, Projects, Files, Messages, Invoices, Payments) belonging to another client.

### Verification Steps
1. Log in as Client A, create a project, and retrieve its ID (`project_id`).
2. Log in as Client B and send a request to `GET /api/client/projects/<project_id>`.
3. Verify that the response returns `403 Forbidden` with the message `"You do not own this resource"`.
4. Log in as `super_admin` or `ops_lead` and send the same request. Verify that the request succeeds (bypasses ownership checks for administrative oversight).

## 3. Rate Limiting Verification

Login and token refresh routes are rate-limited to prevent brute force attacks.

### Verification Steps
1. Send 6 consecutive POST requests to `/api/auth/login` within 60 seconds.
2. Verify that the first 5 requests process normally (either returning success or 401 depending on credentials).
3. Verify that the 6th request is blocked and returns `429 Too Many Requests` with the standard envelope code `"RATE_LIMIT_EXCEEDED"`.

## 4. Immutable Audit Logs Verification

Critical security events (Login, Logout, Role Changes, Invoice/Payment modifications) are recorded in the `audit_logs` collection.

### Verification Steps
1. Perform actions such as login, creating an invoice, or updating tax settings.
2. Query the MongoDB `audit_logs` collection: `db.audit_logs.find()`.
3. Verify that records exist for each action containing:
   - `timestamp` (UTC datetime)
   - `actor` (user identifier)
   - `action` (action string matching the action performed)
   - `target` (resource identifier or route name)
   - `metadata` (relevant payload info)
