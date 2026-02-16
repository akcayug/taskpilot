# TaskPilot - Setup & Deployment Guide

## Local Setup
```bash
cp .env.example .env  # Edit with your values
docker-compose build
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@db:5432/taskpilot` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `SECRET_KEY` | Django secret key | `your-secret-key-here` |
| `DEBUG` | Debug mode (False in production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,taskpilot.com` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token | `1234567890:ABCdefGHI...` |
| `EMAIL_HOST` | SMTP server | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | `user@example.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password | `your-email-password` |
| `EMAIL_USE_TLS` | Use TLS for email | `True` |

## Deployment (Coolify)
1. Push code to Git repository
2. Create new service in Coolify (Docker Compose type)
3. Set environment variables in Coolify dashboard
4. Configure persistent volumes:
   - `postgres-data:/var/lib/postgresql/data`
   - `redis-data:/data`
5. Deploy and wait for all services to start
6. Run migrations: `docker exec <web-container> python manage.py migrate`
7. Create superuser: `docker exec -it <web-container> python manage.py createsuperuser`

## Healthz Contract
Each service exposes `/healthz` endpoint:
- **Response**: `200 OK` with `{"status": "healthy"}`
- **Failure**: `503 Service Unavailable` with error details
- **Checks**: Database connectivity, Redis connectivity (where applicable)

Example:
```bash
curl http://localhost:8000/healthz  # Web service
curl http://localhost:8001/healthz  # Bot service
```

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
