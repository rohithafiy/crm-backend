# Deployment Guide — Portal 5 A1

## Architecture

```
                         ┌─────────────┐
                         │   nginx/caddy   │  (TLS termination)
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  Flask/Gunicorn │  (app: create_app)
                         └──────┬──────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ┌─────▼─────┐          ┌──────▼──────┐
              │   MongoDB  │          │   Redis *   │
              │ (primary)  │          │  (optional) │
              └───────────┘          └─────────────┘
```

## A1 Responsibilities

This deployment covers the Portal 5 A1 contract:
- **Authentication** — login, logout, refresh, me endpoints at `/api/auth/*`
- **Security** — JWT via HTTP-only cookies, RBAC, rate limiting, audit logging
- **Architecture** — middleware pipeline, API governance, standardized responses
- **Integration** — cross-portal communication via HTTP APIs with HMAC signing
- **Deployment** — health checks, environment configuration, Docker support

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir .
ENV FLASK_ENV=production
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    env_file: .env
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

volumes:
  mongo_data:
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `development` | Application environment |
| `FLASK_DEBUG` | No | `1` | Enable debug mode |
| `SECRET_KEY` | **Yes** | `dev-secret-key` | Flask secret key |
| `JWT_SECRET` | **Yes** | `dev-jwt-secret` | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRY` | No | `3600` | Access token TTL (seconds) |
| `JWT_REFRESH_TOKEN_EXPIRY` | No | `86400` | Refresh token TTL (seconds) |
| `MONGO_URI` | **Yes** | `mongodb://localhost:27017/lti_crm` | MongoDB connection string |
| `MONGO_DB_NAME` | No | `lti_crm` | MongoDB database name |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed CORS origins (comma-separated) |
| `CLOUDINARY_CLOUD_NAME` | **Yes** | — | Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | **Yes** | — | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | **Yes** | — | Cloudinary API secret |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | No | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW` | No | `60` | Rate limit window (seconds) |

## Production Checklist

- [ ] Change `SECRET_KEY` and `JWT_SECRET` to strong random values
- [ ] Set `FLASK_ENV=production`
- [ ] Use managed MongoDB (Atlas) or replica set
- [ ] Configure TLS termination via reverse proxy
- [ ] Set `CORS_ORIGINS` to specific origins
- [ ] Enable rate limiting with appropriate thresholds
- [ ] Set up centralized logging (e.g., ELK, Datadog)
- [ ] Configure monitoring and alerting
- [ ] Run database backups on a schedule
- [ ] Use environment-specific `.env` files or secrets manager
