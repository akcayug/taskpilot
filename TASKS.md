# TaskPilot Development Tasks

## TASK-1: Django Multi-Tenant Foundation
**Goal**: Set up Django project with strict multi-tenant architecture and user authentication

**Files**:
- `taskpilot/settings.py`
- `taskpilot/urls.py`
- `core/models.py` (Tenant, User, TenantMembership)
- `core/middleware.py` (TenantMiddleware)
- `core/admin.py`
- `requirements.txt`
- `.env.example`
- `Dockerfile.web`

**Acceptance Criteria**:
- Django project structure created with PostgreSQL configured
- Custom User model with email authentication
- Tenant model with strict isolation (tenant field on all queries)
- TenantMembership model (Manager/Member roles)
- Middleware enforces tenant context on all requests
- Django Admin allows creating tenants (platform admin only)
- `/healthz` endpoint returns 200 with DB check

**Test Command**: `pytest tests/test_tenant_isolation.py`

**Status**: [x] DONE

---

## TASK-2: Project & Task Management Models
**Goal**: Implement Project and Task models with status transitions and business logic

**Files**:
- `tasks/models.py` (Project, Task)
- `tasks/services.py` (TaskService with status transition logic)
- `tasks/admin.py`
- `tests/test_task_transitions.py`

**Acceptance Criteria**:
- Project model with tenant FK and name/description
- Task model with title, assignee, due_date, priority (HIGH/MEDIUM/LOW), status (TODO/IN_PROGRESS/DONE/ARCHIVED)
- TaskService enforces valid status transitions (TODO→IN_PROGRESS→DONE→ARCHIVED)
- Cannot assign task to user outside tenant
- All queries scoped by tenant automatically
- Audit log created on status change

**Test Command**: `pytest tests/test_task_transitions.py`

**Status**: [x] DONE

---

## TASK-3: Web UI - Authentication & Task Dashboard
**Goal**: Build web dashboard with login, task table, filtering, sorting, and export

**Files**:
- `web/templates/base.html`
- `web/templates/login.html`
- `web/templates/dashboard.html`
- `web/views.py` (LoginView, DashboardView, TaskListView)
- `web/urls.py`
- `static/css/styles.css`
- `static/js/dashboard.js` (DataTables integration)

**Acceptance Criteria**:
- Login page (email/password) with tenant-aware authentication
- Dashboard shows tasks in DataTable (title, assignee, due date, priority, status)
- Filtering by status, priority, assignee
- Sorting by all columns
- Pagination (25 per page)
- Export to CSV button
- Bootstrap 5 + Lucide icons used
- Only tasks from current user's tenant visible

**Test Command**: `pytest tests/test_web_ui.py`

**Status**: [x] DONE

---

## TASK-4: Invite System & User Onboarding
**Goal**: Implement email invitation flow with Telegram linking

**Files**:
- `users/models.py` (Invitation)
- `users/views.py` (InviteView, AcceptInviteView, LinkTelegramView)
- `users/tasks.py` (send_invitation_email Celery task)
- `users/templates/invite_email.html`
- `users/urls.py`
- `tests/test_invite_flow.py`

**Acceptance Criteria**:
- Manager can create invitation with email and role (Manager/Member)
- Invitation email sent via Celery with unique token
- User clicks link, sets password, and is added to tenant
- User can link Telegram account via unique code shown in web UI
- Invitation expires after 7 days
- Cannot invite same email twice to same tenant

**Test Command**: `pytest tests/test_invite_flow.py`

**Status**: [x] DONE

---

## TASK-5: Telegram Bot - Task Operations
**Goal**: Build Telegram bot service for creating, listing, and updating tasks

**Files**:
- `bot/main.py` (Bot entry point)
- `bot/handlers.py` (Command and button handlers)
- `bot/keyboards.py` (Inline keyboard builders)
- `bot/api_client.py` (HTTP client to web service API)
- `bot/healthz.py` (Healthz endpoint)
- `Dockerfile.bot`
- `tests/test_bot_handlers.py`

**Acceptance Criteria**:
- Bot starts with `/start` command (links to web UI for account setup)
- `/newtask` command launches button-driven task creation flow
- `/mytasks` shows user's assigned tasks with status
- Inline buttons to update task status (TODO→IN_PROGRESS→DONE)
- All operations verify Telegram user is linked to tenant
- Bot service has `/healthz` endpoint
- Bot uses Telegram API with webhook or polling

**Test Command**: `pytest tests/test_bot_handlers.py`

**Status**: [x] DONE

---

## TASK-6: Celery Workers - Reminders & Notifications
**Goal**: Implement scheduled reminders and notification system

**Files**:
- `workers/celery_app.py` (Celery config)
- `workers/tasks.py` (send_reminder, send_daily_digest)
- `workers/scheduler.py` (Celery Beat schedule)
- `Dockerfile.worker`
- `tests/test_celery_tasks.py`

**Acceptance Criteria**:
- Celery configured with Redis broker
- Daily reminder task checks tasks due today and sends Telegram message
- Daily digest (8 AM) lists all pending tasks for user
- Reminders only sent to users with Telegram linked
- Celery Beat schedule configured
- Worker service has healthz endpoint (Redis connectivity check)

**Test Command**: `pytest tests/test_celery_tasks.py`

**Status**: [x] DONE

---

## TASK-7: Docker Compose & Deployment Setup
**Goal**: Create production-ready Docker Compose setup with all services

**Files**:
- `docker-compose.yml`
- `Dockerfile.web`
- `Dockerfile.bot`
- `Dockerfile.worker`
- `.dockerignore`
- `nginx.conf` (optional reverse proxy)
- `scripts/entrypoint-web.sh`
- `scripts/entrypoint-worker.sh`

**Acceptance Criteria**:
- `docker-compose.yml` defines: web, bot, worker, db (postgres), redis
- All services start successfully with `docker-compose up`
- Web service runs migrations on startup
- Persistent volumes for postgres and redis data
- Environment variables loaded from `.env`
- All services respond to healthz checks
- Coolify-compatible (no custom orchestration)

**Test Command**: `docker-compose up -d && docker-compose ps` (all services healthy)

**Status**: [ ] TODO

---

## TASK-8: Audit Logging & Final Integration Tests
**Goal**: Add audit logging and end-to-end integration tests

**Files**:
- `audit/models.py` (AuditLog)
- `audit/middleware.py` (AuditMiddleware)
- `audit/signals.py` (Task change signals)
- `tests/integration/test_full_workflow.py`
- `README.md`

**Acceptance Criteria**:
- AuditLog model tracks: user, action, resource_type, resource_id, changes, timestamp
- Middleware logs all task status changes
- Integration test: Create tenant → Invite user → Create task → Update via bot → Verify in web UI
- No cross-tenant data leakage in any scenario
- README documents setup, deployment, and architecture

**Test Command**: `pytest tests/integration/`

**Status**: [ ] TODO
