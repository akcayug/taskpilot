# PROJECT_SPEC.md

## What
TaskPilot is a multi-tenant, Telegram-first task management system designed for teams that need fast, structured task execution without complexity. It combines a powerful web dashboard with a streamlined bot interface to create, assign, prioritize, and track tasks efficiently in real time.

## Project Scope
- Multi-tenant architecture (strict tenant isolation)
- Tenant management via Django Admin (platform level only)
- Two tenant roles: Manager and Member
- Projects per tenant
- Tasks with title, assignee, due date, priority, and status
- Backend-enforced status transitions
- Web UI with task table (filtering, sorting, pagination, export)
- Invite-based user onboarding (email + Telegram linking)
- Telegram bot (button-driven task creation, task listing, status updates, reminders)
- Scheduled notifications
- Audit logging
- Docker Compose deployment (web, bot, worker, db, redis)
- Healthcheck endpoints

## Non-Scope (MVP dışı)
- Public registration
- Payments or subscriptions
- Kanban board
- Gantt or timeline views
- File attachments
- Real-time WebSockets
- External integrations
- AI-based automation
- Cross-tenant collaboration
- Plugin or marketplace system

## Tech Stack
- Django
- PostgreSQL
- UI framework: Bootstrap 5 + DataTables + Lucide icons
- Redis + Celery (scheduled jobs & reminders)
- Separate Telegram Bot service
- Docker Compose multi-service setup
- Coolify-compatible deployment
- Strict tenant isolation at database and application level

## Success Criteria
- Application deploys successfully via Docker Compose and runs without errors (web, bot, worker, db, redis).
- All services respond correctly to /healthz.
- A tenant is created via Django Admin.
- A Manager user is created and can log into the web UI.
- The Manager invites one Member user (email + Telegram linked).
- The Member can:
- Access the web UI
- Create a task
- See assigned tasks
- Use the Telegram bot
- Task status updates and reminders work as expected.
- No cross-tenant data is visible at any point.