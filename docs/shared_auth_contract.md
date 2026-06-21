# Shared Authentication Contract

## Overview

This document defines the complete multi-portal authentication lifecycle for the LTI Hub platform.
Portal 5 serves as the authentication backbone, issuing and managing JWT tokens that are shared across all portals.

**Implementation:** `app/services/auth_service.py`, `app/middleware/auth_middleware.py`, `app/utils/jwt_helper.py`

---

## Approved Authentication Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|:---:|-------------|
| `/api/auth/login` | POST | ❌ | Authenticate user and issue tokens |
| `/api/auth/logout` | POST | ❌ | Revoke current session |
| `/api/auth/refresh` | POST | ❌ | Rotate access token using refresh token |
| `/api/auth/me` | GET | ✅ | Retrieve current authenticated user profile |

---

## 1. Login Flow

### Request
```
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

### Flow Sequence

```
Client                    Portal 5                    Database
  │                          │                           │
  │──POST /api/auth/login──▶│                           │
  │                          │──validate input──▶        │
  │                          │──check lockout──▶         │
  │                          │──find user────────────────▶│
  │                          │◀──user record─────────────│
  │                          │──verify password──▶       │
  │                          │──check is_active──▶       │
  │                          │──generate tokens──▶       │
  │                          │──store session────────────▶│
  │                          │──set cookies──▶           │
  │◀──200 + Set-Cookie──────│                           │
```

### Processing Steps

1. **Input Validation** — Validates `email` and `password` per `LOGIN_RULES`
2. **Account Lockout Check** — Rejects if too many failed attempts (threshold: `ACCOUNT_LOCKOUT_THRESHOLD`)
3. **User Lookup** — Queries `users` collection by email
4. **Password Verification** — bcrypt comparison against stored `password_hash`
5. **Failed Login Recording** — Increments lockout counter on failure
6. **Active Status Check** — Rejects deactivated accounts with `ACCOUNT_DEACTIVATED`
7. **Role Resolution** — Resolves `role` (singular) and `roles` (list) from user record
8. **Token Generation** — Creates access + refresh token pair
9. **Session Recording** — Stores session with JTI, IP, user agent
10. **Cookie Setting** — Sets `access_token` and `refresh_token` as HTTP-only secure cookies

### Response
```json
{
  "status": "success",
  "code": 200,
  "data": null,
  "message": "Login successful",
  "metadata": {
    "api_version": "v1",
    "timestamp": "2026-06-18T12:00:00.000000+00:00"
  }
}
```

### Cookies Set

| Cookie | Path | HttpOnly | Secure | SameSite | Max-Age |
|--------|------|:---:|:---:|:---:|---------|
| `access_token` | `/` | ✅ | ✅ | Strict | `JWT_ACCESS_TOKEN_EXPIRY` |
| `refresh_token` | `/api/auth` | ✅ | ✅ | Strict | `JWT_REFRESH_TOKEN_EXPIRY` |

### Rate Limiting
- **5 requests per minute** per IP address

---

## 2. JWT Lifecycle

### Access Token

**Purpose:** Authenticates API requests across all portals.

**Payload Schema:**
```json
{
  "sub": "user_object_id",
  "role": "project_manager",
  "roles": ["project_manager"],
  "portals": ["portal5", "portal3"],
  "type": "access",
  "jti": "uuid-v4",
  "iat": 1718712000,
  "nbf": 1718712000,
  "exp": 1718715600
}
```

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | `string` | User ID (MongoDB ObjectId as string) |
| `role` | `string` | **Primary role** — canonical claim per shared user schema |
| `roles` | `array[string]` | Full role list (supplementary, for backward compatibility) |
| `portals` | `array[string]` | Authorized portal identifiers |
| `type` | `string` | Always `"access"` |
| `jti` | `string` | Unique token identifier (UUID v4) |
| `iat` | `integer` | Issued-at timestamp |
| `nbf` | `integer` | Not-before timestamp |
| `exp` | `integer` | Expiration timestamp |

**Algorithm:** HS256
**Secret:** `JWT_SECRET` environment variable

### Refresh Token

**Purpose:** Obtain new access tokens without re-authentication.

**Payload Schema:**
```json
{
  "sub": "user_object_id",
  "type": "refresh",
  "jti": "uuid-v4",
  "iat": 1718712000,
  "nbf": 1718712000,
  "exp": 1718798400
}
```

Refresh tokens contain **no role or portal claims** — these are re-fetched from the database on refresh.

### Token Expiry Configuration

| Token | Env Variable | Default |
|-------|-------------|---------|
| Access | `JWT_ACCESS_TOKEN_EXPIRY` | 3600s (1 hour) |
| Refresh | `JWT_REFRESH_TOKEN_EXPIRY` | 86400s (24 hours) |

---

## 3. Portal Routing

### Portal Validation

On login, the user's `portals` field is validated against the approved portal set:

```
Valid Portals: portal1, portal3, portal5, portal6, portal8
```

Invalid portal identifiers are silently stripped from the token.

### Portal-Specific Access

The `portals` claim in the JWT determines which portal APIs a user can access:

| Portal | System | Access Scope |
|--------|--------|-------------|
| `portal1` | Project Requests | Submit/track project requests |
| `portal3` | Workspace | Client workspace and project association |
| `portal5` | CRM | Full CRM operations (this system) |
| `portal6` | Performance | View performance metrics and scores |
| `portal8` | Automation | Trigger workflows and notifications |

### Middleware Resolution

The `AuthMiddleware` extracts portal claims and sets `g.portals` on every authenticated request:

```python
g.portals = payload.get("portals", [])
```

---

## 4. Cross-Portal Sessions

### Shared JWT Architecture

All portals share the same JWT secret and algorithm, enabling a single token to authenticate across portal boundaries:

```
Portal 5 (Login) ──issues JWT──▶ Client
                                   │
Client ──presents same JWT──▶ Portal 1
Client ──presents same JWT──▶ Portal 3
Client ──presents same JWT──▶ Portal 6
Client ──presents same JWT──▶ Portal 8
```

### Session State

Sessions are tracked centrally in Portal 5's `sessions` collection:

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | `string` | Owning user |
| `access_jti` | `string` | Access token JTI |
| `refresh_jti` | `string` | Refresh token JTI |
| `created_at` | `datetime` | Session creation time |
| `expires_at` | `datetime` | Session expiration time |
| `ip_address` | `string` | Client IP at creation |
| `user_agent` | `string` | Client User-Agent at creation |
| `is_active` | `boolean` | Session active flag |

### Token Blacklist

Revoked tokens are tracked in the `token_blacklist` collection:

| Field | Type | Description |
|-------|------|-------------|
| `jti` | `string` | Token JTI |
| `type` | `string` | Token type (`access`, `refresh`, `session`, `session_revoked`) |
| `user_id` | `string` | Associated user (optional) |
| `revoked_at` | `datetime` | Revocation timestamp |

---

## 5. Logout Flow

### Single Session Logout

```
POST /api/auth/logout
```

1. Extract token from cookie or `Authorization: Bearer` header
2. Decode token payload
3. Add token JTI to `token_blacklist`
4. Deactivate all active sessions for the user
5. Clear `access_token` and `refresh_token` cookies
6. Return `200 — Logged out successfully`

**Graceful handling:** If no token is present, cookies are cleared and success is returned.

### All Sessions Logout

```
POST /api/auth/logout/all
```

**Requires authentication.**

1. Find all active sessions for `g.user_id`
2. Blacklist every `access_jti` and `refresh_jti` from each session
3. Mark all sessions as `is_active: false`
4. Clear cookies
5. Return `200 — All sessions terminated`

---

## 6. Refresh Flow

### Request
```
POST /api/auth/refresh
```

No request body — the refresh token is read from the `refresh_token` cookie.

### Flow Sequence

```
Client                    Portal 5                    Database
  │                          │                           │
  │──POST /api/auth/refresh──▶│                          │
  │                          │──read refresh cookie──▶   │
  │                          │──decode token──▶          │
  │                          │──verify type=refresh──▶   │
  │                          │──check blacklist──────────▶│
  │                          │──find user────────────────▶│
  │                          │──check is_active──▶       │
  │                          │──revoke old session───────▶│
  │                          │──blacklist old token───────▶│
  │                          │──generate new tokens──▶   │
  │                          │──store new session────────▶│
  │                          │──set new cookies──▶       │
  │◀──200 + Set-Cookie──────│                           │
```

### Processing Steps

1. Read `refresh_token` from cookie
2. Decode and validate token (must be `type: refresh`)
3. Verify JTI is not blacklisted
4. Look up user by `sub` claim
5. Verify user is still active
6. **Rotate:** Deactivate old session and blacklist old refresh JTI
7. Re-fetch current `role`/`roles` and `portals` from database
8. Generate new access + refresh token pair
9. Store new session
10. Set new cookies

### Token Rotation

Refresh token rotation ensures that:
- Each refresh token can only be used **once**
- Old refresh tokens are immediately blacklisted
- If a stolen refresh token is replayed, it will be rejected

### Rate Limiting
- **5 requests per minute** per IP address

---

## Security Controls

| Control | Implementation |
|---------|---------------|
| Password hashing | bcrypt with 12 rounds |
| Token signing | HS256 with shared secret |
| Cookie security | HttpOnly, Secure, SameSite=Strict |
| Account lockout | Configurable threshold and duration |
| Token blacklisting | JTI-based revocation |
| Rate limiting | Per-endpoint IP-based limits |
| CORS | Whitelist-only origins |
| Audit logging | All auth events logged via `log_audit()` |
