# TaskPilot

A multi-tenant task management system with Telegram bot integration, built with Django and designed for deployment on Coolify.

## Features

- 🏢 **Multi-Tenant Architecture** - Strict tenant isolation with automatic data scoping
- 📱 **Telegram Bot Integration** - Manage tasks directly from Telegram
- 👥 **User Management** - Email-based invitations with role-based access (Manager/Member)
- ✅ **Task Management** - Create, assign, and track tasks with priorities and due dates
- 📊 **Web Dashboard** - Clean, responsive UI with DataTables for filtering and sorting
- 📧 **Email Notifications** - Automated invitations via SMTP
- ⏰ **Scheduled Reminders** - Daily digests and due date notifications via Telegram
- 📝 **Audit Logging** - Complete audit trail of all changes
- 🔒 **Security** - Email authentication, tenant isolation, and secure token-based invitations

## Tech Stack

- **Backend**: Django 4.2, PostgreSQL, Redis
- **Task Queue**: Celery with Celery Beat for scheduling
- **Bot**: python-telegram-bot
- **Frontend**: Bootstrap 5, DataTables, Lucide Icons
- **Deployment**: Docker Compose, Coolify

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Coolify                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   Docker Compose                       │  │
│  │                                                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │  │
│  │  │   Web    │  │   Bot    │  │     Worker       │    │  │
│  │  │ (Django) │  │(Telegram)│  │(Celery+Beat)     │    │  │
│  │  │  :8000   │  │  :8001   │  │     :8002        │    │  │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │  │
│  │       │             │                  │               │  │
│  │       └─────────────┼──────────────────┘               │  │
│  │                     │                                   │  │
│  │       ┌─────────────┴──────────────┐                   │  │
│  │       │                             │                   │  │
│  │  ┌────▼─────┐               ┌──────▼─────┐            │  │
│  │  │PostgreSQL│               │   Redis    │            │  │
│  │  │  :5432   │               │   :6379    │            │  │
│  │  └──────────┘               └────────────┘            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Services

1. **Web Service** - Django application with Gunicorn
   - REST API for bot integration
   - Web dashboard for task management
   - User authentication and authorization
   - Health check endpoint: `/healthz`

2. **Bot Service** - Telegram bot
   - Task creation and updates
   - Task listing and status changes
   - Telegram account linking
   - Health check endpoint: `:8001/healthz`

3. **Worker Service** - Celery worker with Beat scheduler
   - Daily reminders (8 AM UTC)
   - Due today notifications (9 AM UTC)
   - Overdue reminders
   - Cleanup tasks (expired invitations, tokens)
   - Health check endpoint: `:8002/healthz`

4. **Database** - PostgreSQL 15
   - Primary data store
   - Persistent volume: `postgres_data`

5. **Cache/Broker** - Redis 7
   - Celery message broker
   - Cache backend
   - Persistent volume: `redis_data`

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/taskpilot.git
cd taskpilot

# Configure environment
cp .env.example .env
# Edit .env with your values (SECRET_KEY, DB passwords, TELEGRAM_BOT_TOKEN)

# Start all services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access the application
open http://localhost:8000
```

### Production Deployment (Coolify)

1. **Push to Git**
   ```bash
   git push origin main
   ```

2. **Create Service in Coolify**
   - Type: Docker Compose
   - Repository: Your Git repository
   - Branch: main

3. **Configure Environment Variables**
   Set these in Coolify dashboard (see `.env.example`):
   - `SECRET_KEY` - Django secret key (50+ random chars)
   - `DB_PASSWORD` - PostgreSQL password
   - `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
   - `ALLOWED_HOSTS` - Your domain (e.g., `taskpilot.example.com`)

4. **Deploy**
   - Coolify will automatically map port 8000 to your domain
   - Migrations run automatically on startup
   - Wait for all services to be healthy

5. **Create Superuser**
   ```bash
   docker exec -it <web-container> python manage.py createsuperuser
   ```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

**Required Variables:**
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `CELERY_BROKER_URL` - Redis URL for Celery

**Optional Variables:**
- `DEBUG` - Set to `False` in production
- `ALLOWED_HOSTS` - Comma-separated list of allowed domains
- `EMAIL_HOST`, `EMAIL_PORT`, etc. - SMTP configuration for invitations

### Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get the bot token
3. Set `TELEGRAM_BOT_TOKEN` in your environment
4. Deploy the application
5. Test with `/start` command

## Usage

### Web Dashboard

1. **Login** - Navigate to your domain and log in with your email
2. **Dashboard** - View task statistics and task list
3. **Filter & Sort** - Use DataTables controls to filter by status, priority, assignee
4. **Export** - Click "Export CSV" to download task list
5. **Invite Users** - Managers can invite new members via email

### Telegram Bot

**Commands:**
- `/start` - Start the bot and link your account
- `/link <code>` - Link your Telegram account with code from web UI
- `/mytasks` - View your assigned tasks
- `/newtask` - Create a new task (interactive flow)
- `/task <id>` - View task details and update status

**Workflow:**
1. User signs up via web invitation
2. User goes to "Link Telegram" in web UI
3. User copies the 8-character code
4. User sends `/link <code>` to bot
5. User can now manage tasks via Telegram

### Task Status Workflow

```
TODO → IN_PROGRESS → DONE → ARCHIVED
  ↓         ↓         ↓
  └─────────┴─────────┴─→ ARCHIVED
```

**Valid Transitions:**
- TODO → IN_PROGRESS, ARCHIVED
- IN_PROGRESS → DONE, TODO, ARCHIVED
- DONE → ARCHIVED
- ARCHIVED → (no transitions allowed)

## Development

### Project Structure

```
taskpilot/
├── core/              # Multi-tenant core (User, Tenant, Middleware)
├── tasks/             # Task and Project models, services
├── users/             # Invitation system, Telegram linking
├── audit/             # Audit logging, signals, middleware
├── web/               # Web dashboard views and templates
├── bot/               # Telegram bot handlers and keyboards
├── workers/           # Celery tasks and scheduling
├── templates/         # Django templates
├── static/            # CSS, JS, images
├── tests/             # Unit and integration tests
│   ├── test_*.py      # Unit tests
│   └── integration/   # Integration tests
├── scripts/           # Entrypoint scripts for Docker
├── docker-compose.yml # Service orchestration
├── Dockerfile.*       # Service-specific Dockerfiles
└── requirements.txt   # Python dependencies
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_tenant_isolation.py

# Run integration tests only
pytest tests/integration/
```

**Test Coverage:** 106+ tests covering:
- Multi-tenant isolation (17 tests)
- Task transitions and business logic (21 tests)
- Web UI and API endpoints (18 tests)
- Invitation flow (21 tests)
- Telegram bot handlers (17 tests)
- Celery tasks (12 tests)
- Integration tests (3+ tests)

### Code Quality

The project follows these principles:
- **One task at a time** - Focus on completing tasks fully before moving on
- **No premature refactoring** - Only refactor when explicitly needed
- **Strict tenant isolation** - All queries automatically scoped by tenant
- **Audit everything** - All changes logged via signals
- **Health checks** - All services expose `/healthz` endpoints
- **Security first** - No secrets in code, environment variables only

## Monitoring

### Health Checks

Each service exposes a health check endpoint:

```bash
# Web service
curl http://localhost:8000/healthz
# Response: {"status": "healthy"}

# Bot service
curl http://localhost:8001/healthz
# Response: {"status": "healthy"}

# Worker service
curl http://localhost:8002/healthz
# Response: {"status": "healthy", "service": "worker"}
```

Health checks verify:
- **Web**: Database connectivity
- **Bot**: Service is running
- **Worker**: Redis connectivity

### Logs

View logs for each service:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f bot
docker-compose logs -f worker
```

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```
Error: django.db.utils.OperationalError: could not connect to server
```
Fix: Check `DATABASE_URL` and verify PostgreSQL is running
```bash
docker-compose ps db
```

**2. Redis Connection Timeout**
```
Error: redis.exceptions.ConnectionError
```
Fix: Verify Redis is healthy
```bash
docker-compose ps redis
docker-compose logs redis
```

**3. Telegram Bot Not Responding**
```
Bot doesn't reply to commands
```
Fix: Check bot token and logs
```bash
docker-compose logs bot
# Verify TELEGRAM_BOT_TOKEN is correct
```

**4. Migrations Not Applied**
```
Error: django.db.utils.ProgrammingError: relation does not exist
```
Fix: Migrations run automatically, but you can run manually:
```bash
docker-compose exec web python manage.py migrate
```

**5. Static Files 404**
```
404 errors for CSS/JS files
```
Fix: Collect static files
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Reset Database

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker volume rm taskpilot_postgres_data taskpilot_redis_data

# Start fresh
docker-compose up -d
```

## Security

- **Authentication**: Email-based with secure password hashing
- **Tenant Isolation**: Middleware enforces tenant context on all requests
- **Secrets Management**: All secrets in environment variables
- **Invitation Tokens**: Secure random tokens with 7-day expiration
- **Telegram Linking**: 8-character codes with 24-hour expiration
- **Audit Trail**: All changes logged with user and timestamp
- **CSRF Protection**: Django CSRF middleware enabled
- **SQL Injection**: Django ORM with parameterized queries

## Contributing

This project follows a task-based development workflow. See `TASKS.md` for the breakdown of completed tasks.

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [Your Repo URL]
- Documentation: See `INSTRUCTIONS.md` and `CLAUDE.md`

---

Built with ❤️ using Django, Celery, and Telegram Bot API
