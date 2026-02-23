# TaskPilot - Project Specification

## What
TaskPilot is a multi-tenant task management system that combines a web dashboard with a Telegram bot for fast, structured task execution. Teams create, assign, prioritize, and track tasks in real time.

## Scope
- Multi-tenant architecture with strict tenant isolation
- Two roles: Manager (invite users, full access) and Member (assigned tasks only)
- Projects per tenant
- Tasks: title, description, assignee, due date, priority (HIGH/MEDIUM/LOW), status
- Status workflow: TODO → IN_PROGRESS → DONE → ARCHIVED (backend-enforced)
- Web UI: DataTables-based task list with filtering, sorting, pagination, CSV export
- Invite-based user onboarding (email + Telegram linking)
- Telegram bot: button-driven task creation, task listing, status updates, reminders
- Scheduled notifications (daily digest, due date reminders)
- Audit logging for all task changes
- Docker Compose deployment (web, bot, worker, db, redis)
- Healthcheck endpoints for all services

## Non-Scope (Out of MVP)
- Public registration or self-service signup
- Payments, subscriptions, or billing
- Kanban board or drag-and-drop UI
- Gantt charts or timeline views
- File attachments or comments
- Real-time WebSockets
- External integrations (Slack, Jira, etc.)
- AI-based automation
- Cross-tenant collaboration
- Plugin system or marketplace

## Tech Stack
- Backend: Django 4.2, PostgreSQL 15, Redis 7
- Task queue: Celery + Celery Beat
- Bot: python-telegram-bot (polling mode)
- Frontend: Bootstrap 5, DataTables, Lucide icons
- Deployment: Docker Compose, Coolify-compatible

## Core Models
- **Tenant**: Organization container for all data
- **User**: Custom user with email auth, linked to tenant via TenantMembership
- **TenantMembership**: User-tenant relationship with role (Manager/Member)
- **Project**: Named container for tasks within tenant
- **Task**: Core entity with assignee, due date, priority, status
- **Invitation**: Email-based invite with token (7-day expiry)
- **AuditLog**: Change tracking for all task modifications

## Permission Model
- **Manager**: Invite users, create/assign/update any task, manage projects
- **Member**: View assigned tasks, update own task status, create tasks

## UI Principles
- Desktop: DataTables for high-density task lists with advanced filtering
- Mobile: Responsive card layout for tasks
- No real-time updates (manual refresh)
- CSV export for reporting

## Telegram Bot Capabilities
- `/start`: Link account instruction
- `/link <code>`: Link Telegram to web account (8-char code, 24h expiry)
- `/newtask`: Interactive task creation (buttons select project, assignee, priority, due date)
- `/mytasks`: List assigned tasks with inline status update buttons
- Daily digest (8 AM UTC): Pending tasks summary
- Due today reminders (9 AM UTC): Tasks due within 24h
