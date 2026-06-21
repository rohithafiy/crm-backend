# Portal 5 — Deployment Security Checklist

This document details the critical security controls and environment verifications required before deploying the Portal 5 CRM & Client Management backend to the production Environment on Render.

## 1. Environment Variables Production Parity

All production environments must explicitly configure and override local defaults:

- [ ] **`FLASK_ENV`**: Set to `production` or `staging`. Never run with `development`.
- [ ] **`SECRET_KEY`**: Cryptographically secure random key. Generated using `openssl rand -hex 32`.
- [ ] **`JWT_SECRET`**: High-entropy secret key specifically for signing JSON Web Tokens. Must be distinct from `SECRET_KEY`.
- [ ] **`MONGO_URI`**: Production MongoDB Atlas connection string. Must use TLS (`tls=true`) and restrict network access to Render backend IPs.
- [ ] **`MONGO_DB_NAME`**: Set to the production database instance name.
- [ ] **`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`**: Production-specific Cloudinary credentials.
- [ ] **`PORTAL1_API_KEY`, `PORTAL3_API_KEY`, `PORTAL6_API_KEY`, `PORTAL8_API_KEY`**: Hardened API tokens for communicating with other portals. Empty values will crash gunicorn startup in production mode.
- [ ] **`PORTAL_WEBHOOK_SECRET`**: Signature secret for verifying incoming webhooks.

## 2. JWT Secret Security

- [ ] JWT keys must have a minimum length of 32 bytes (256 bits).
- [ ] Rotate JWT secrets every 90 days or immediately upon team member access revocation.
- [ ] Tokens must use HTTP-only, Secure=True, and SameSite=Strict cookies to protect against Cross-Site Scripting (XSS) and Cross-Site Request Forgery (CSRF).

## 3. Cloudinary and Third-Party Security Keys

- [ ] API keys must never be committed to repository files (checked by pre-commit hooks).
- [ ] API usage must enforce HTTPS endpoints for all uploads.

## 4. SMTP and Communications Configurations

- [ ] All mail servers must use Secure SMTP (SMTPS/TLS) over port 465 or STARTTLS over port 587.
- [ ] Disable anonymous mailing. Enforce username/password authentication for SMTP.

## 5. Production Configuration Flags

- [ ] **`DEBUG`** is set to `False`.
- [ ] CORS is strictly governed and set to whitelisted domains in `SecurityConfig.CORS_WHITELIST`. Wildcards (`*`) are disallowed.
- [ ] Rate limits are active (`RATE_LIMIT_ENABLED=true`) with login/refresh routes restricted to 5 attempts per minute.
