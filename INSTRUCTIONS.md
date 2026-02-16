# TaskPilot - Setup & Deployment Guide

## Local Setup
```bash
# 1. Configure environment
cp .env.example .env  # Edit with your actual values

# 2. Build and start all services
docker-compose up -d

# 3. Wait for services to be healthy (migrations run automatically)
docker-compose ps

# 4. Create superuser
docker-compose exec web python manage.py createsuperuser
```

**Note**: The web service automatically runs migrations on startup via entrypoint script.

## Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `DB_NAME` | PostgreSQL database name | `taskpilot` |
| `DB_USER` | PostgreSQL username | `taskpilot` |
| `DB_PASSWORD` | PostgreSQL password | `changeme_in_production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@db:5432/taskpilot` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://redis:6379/0` |
| `SECRET_KEY` | Django secret key (50+ chars) | `your-secret-key-here` |
| `DEBUG` | Debug mode (False in production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `*` (or `example.com,www.example.com`) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token | `1234567890:ABCdefGHI...` |
| `WEB_SERVICE_URL` | Web service URL for bot | `http://web:8000` |
| `EMAIL_HOST` | SMTP server (optional) | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port (optional) | `587` |
| `EMAIL_HOST_USER` | SMTP username (optional) | `user@example.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password (optional) | `your-email-password` |
| `EMAIL_USE_TLS` | Use TLS for email (optional) | `True` |

## Deployment (Coolify)
1. Push code to Git repository
2. Create new service in Coolify (Docker Compose type)
3. Set environment variables in Coolify dashboard (see .env.example)
4. Configure persistent volumes:
   - `postgres_data:/var/lib/postgresql/data`
   - `redis_data:/data`
5. Deploy and wait for all services to start (migrations run automatically)
6. Create superuser: `docker exec -it <web-container> python manage.py createsuperuser`

**Note**: Coolify will automatically map port 8000 from the web service to your domain.

## Healthz Contract
Each service exposes `/healthz` endpoint:
- **Response**: `200 OK` with `{"status": "healthy"}`
- **Failure**: `503 Service Unavailable` with error details
- **Checks**: Database connectivity, Redis connectivity (where applicable)

Example:
```bash
curl http://localhost:8000/healthz  # Web service (port 8000)
curl http://localhost:8001/healthz  # Bot service (port 8001)
curl http://localhost:8002/healthz  # Worker service (port 8002)
```

All services include health checks in docker-compose.yml for automatic restart on failure.

## Common Errors

### 1. Database Connection Failed
**Symptom**: `django.db.utils.OperationalError: could not connect to server`
**Fix**: Verify `DATABASE_URL` is correct and PostgreSQL container is running

### 2. Redis Connection Timeout
**Symptom**: `redis.exceptions.ConnectionError: Error connecting to Redis`
**Fix**: Check `REDIS_URL` and ensure Redis container is healthy

### 3. Telegram Bot Not Responding
**Symptom**: Bot doesn't reply to commands
**Fix**: Verify `TELEGRAM_BOT_TOKEN` is valid and bot service is running

### 4. Migrations Not Applied
**Symptom**: `django.db.utils.ProgrammingError: relation does not exist`
**Fix**: Run `docker-compose exec web python manage.py migrate`

### 5. Static Files Not Loading
**Symptom**: 404 errors for CSS/JS files
**Fix**: Run `docker-compose exec web python manage.py collectstatic --noinput`
