# LTI Hub Backend

Multi-portal CRM backend with authentication, authorization, RBAC, and cross-portal integration.

## Quick Start

```bash
# Clone and enter directory
cd lti-hub-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install .

# Copy environment config
cp .env.example .env
# Edit .env with your settings

# Run the app
flask run
```

## Project Structure

```
app/
├── middleware/    # Auth middleware, security headers
├── services/      # Business logic (auth, leads, clients, proposals, invoices, payments, analytics, integration)
├── utils/         # Helpers (JWT, roles, permissions, validation, API responses, DB)
├── configs/       # Environment & security configuration
docs/              # API contracts, integration contracts, deployment guide
tests/             # Pytest suite
```

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | Public | Health check |
| `/auth/register` | POST | Public | Register user |
| `/auth/login` | POST | Public | Login |
| `/auth/refresh` | POST | Public | Refresh token |
| `/auth/me` | GET | Bearer | Current user |
| `/integration/webhook` | POST | Signature | Cross-portal webhook |

See `docs/api_contracts.md` for full details.

## Environment Variables

See `.env.example` for all configurable variables.

## Testing

```bash
pytest tests/ -v
```

## Deployment

See `docs/deployment_guide.md` for Docker setup and production checklist.
