# Development Rules for Claude

## Product Summary
TaskPilot is a multi-tenant task management system with Telegram bot integration. Teams create, assign, and track tasks via web dashboard or Telegram. Managers invite Members. All data is tenant-isolated.

## Core Principles
- **One task at a time**: Complete current task fully before moving to next
- **No refactoring**: Only refactor if explicitly requested in task scope
- **Stop on ambiguity**: When requirements unclear, write `# TODO: clarify [specific question]` and stop
- **Secrets management**: All secrets MUST go in `.env` file, never hardcoded

## Testing
- Test command: `pytest`
- Run tests after every code change
- Do not proceed if tests fail
- Test files must be in `tests/` directory

## Code Quality
- Follow Django best practices
- Use type hints where beneficial
- Keep functions focused and small
- Write docstrings for complex logic only
- Avoid over-engineering: implement only what's asked

## Git Workflow
- Commit after completing each task
- Commit message format: `TASK-X: [description]`
- Never commit `.env` or secrets
- Never use `--no-verify` unless explicitly requested

## Required Endpoints
- Every service MUST implement `/healthz` endpoint
- Healthz must return `200 OK` with `{"status": "healthy"}`
- Include database/Redis connectivity check where applicable

## When Stuck
1. Check existing Django/Celery/Telegram bot documentation
2. Write explicit TODO with question in code
3. Ask user for clarification
4. Do NOT guess or make assumptions

## Security
- Never commit credentials
- Validate all user input
- Enforce tenant isolation on all queries
- No destructive git operations without confirmation

## Task Execution Protocol
- Work on one task at a time
- For each task, read only: CLAUDE.md, PROJECT_SPEC.md, task-docs/TASK-XX file
- After acceptance criteria pass → mark [x] in TASKS.md
- If architecture changes → update PROJECT_SPEC.md (stay within 70 lines)
- Stop after completing one task
- Do not auto-start next task
- After TASK-08 completion → delete TASK_BLUEPRINT.md, TASKS.md, /task-docs directory

## Documentation
- See `PROJECT_SPEC.md` for architecture and scope
- See `README.md` for setup and deployment
- Keep docs under 70 lines each
