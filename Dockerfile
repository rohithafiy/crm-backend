FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir .
ENV FLASK_ENV=production
EXPOSE 5000
# Use a reverse proxy (nginx/caddy) in front for TLS termination
CMD ["gunicorn", "--bind", "127.0.0.1:5000", "app:create_app()"]
