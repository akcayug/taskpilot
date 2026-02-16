# Development Rules for Claude

## Core Principles
- **One task at a time**: Complete current task fully before moving to next
- **No refactoring**: Only refactor if explicitly requested in task scope
- **Stop on ambiguity**: When requirements are unclear, write `# TODO: clarify [specific question]` and stop
- **Secrets management**: All secrets MUST go in `.env` file, never hardcoded

## Testing
- Test command: `pytest`
- Run tests after every code change
- Do not proceed if tests fail

## Required Endpoints
- Every service MUST implement `/healthz` endpoint
- Healthz must return 200 OK when service is ready
- Include database connectivity check in healthz

## Code Quality
- Follow Django best practices
- Use type hints where beneficial
- Keep functions focused and small
- Write docstrings for complex logic only

## Git Workflow
- Commit after completing each task
- Use descriptive commit messages: "TASK-X: [description]"
- Do not commit `.env` or secrets

## When Stuck
1. Check existing Django/Celery/Telegram bot documentation
2. Write explicit TODO with question
3. Ask user for clarification
4. Do NOT guess or make assumptions
