# LTI Hub Backend — Portal 5 A1

Authentication, security, architecture, and integration layer for the LTI multi-portal CRM platform.

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
├── services/      # Auth, integration, security, deployment
├── utils/         # Helpers (JWT, roles, permissions, validation, API responses, DB)
├── configs/       # Environment & security configuration
docs/              # API contracts, integration contracts, deployment guide
tests/             # Pytest suite
```

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | Public | Health check |
| `/api/auth/login` | POST | Public | Login |
| `/api/auth/refresh` | POST | Public | Refresh token |
| `/api/auth/me` | GET | Bearer/Cookie | Current user |
| `/api/auth/verify` | GET | Bearer/Cookie | Verify token |
| `/integration/webhook` | POST | Signature | Cross-portal webhook |

## Environment Variables

See `.env.example` for all configurable variables.

## Testing

```bash
pytest tests/ -v
```

## Deployment

See `docs/deployment_guide.md` for Docker setup and production checklist.
