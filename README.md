# TaskPilot

Multi-tenant task management system with Telegram bot integration. Manage tasks via web dashboard or Telegram.

## Quick Start

```bash
# Clone and configure
git clone <repo-url>
cd taskpilot
cp .env.example .env
# Edit .env with your values

# Start all services
docker-compose up -d

# Wait for healthy status
docker-compose ps

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access application
open http://localhost:8000
```

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret (50+ chars) | `your-secret-key-here` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@db:5432/taskpilot` |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | `1234567890:ABC...` |
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://redis:6379/0` |
| `ALLOWED_HOSTS` | Comma-separated domains | `*` or `example.com` |
| `DEBUG` | Debug mode (False in prod) | `False` |

See `.env.example` for all variables including optional SMTP settings.

## Services

1. **Web** (`:8000`) - Django application, REST API, web dashboard
2. **Bot** (`:8001`) - Telegram bot service
3. **Worker** (`:8002`) - Celery worker + Beat scheduler
4. **PostgreSQL** (`:5432`) - Primary database
5. **Redis** (`:6379`) - Celery broker + cache

## Health Checks

Each service exposes `/healthz`:

```bash
curl http://localhost:8000/healthz  # Web
curl http://localhost:8001/healthz  # Bot
curl http://localhost:8002/healthz  # Worker
```

Response: `{"status": "healthy"}` (200 OK)

## Usage

### Web Dashboard
1. Log in with email/password
2. Managers: Invite users via email
3. View/filter/sort tasks with DataTables
4. Export tasks to CSV

### Telegram Bot
1. Get invite email and set password on web
2. Go to "Link Telegram" in web UI
3. Copy 8-character code
4. Send `/link <code>` to bot
5. Use `/mytasks`, `/newtask` commands

## Documentation

- **CLAUDE.md** - Development rules and workflow
- **PROJECT_SPEC.md** - Architecture, scope, and models

## Troubleshooting

**Database connection failed**: Check `DATABASE_URL` and `docker-compose ps db`
**Bot not responding**: Verify `TELEGRAM_BOT_TOKEN` and check `docker-compose logs bot`
**Tests failing**: Run `pytest` and check test output

## Testing

```bash
pytest                    # Run all tests
pytest --cov=.           # With coverage
pytest tests/integration/ # Integration tests only
```
