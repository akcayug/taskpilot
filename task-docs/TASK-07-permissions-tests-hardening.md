# TASK-07: Permissions Tests + Hardening

## Goal
Comprehensive permission testing and enforcement across all endpoints (web + bot).

## Scope
- Verify tenant isolation (no cross-tenant data leakage)
- Verify RBAC (manager vs member permissions)
- Add tests for:
  - Tenant isolation
  - Inline edit endpoints
  - Settings endpoints
  - Bot API endpoints
  - Financial snapshot endpoints
- Ensure all queries are tenant-scoped
- Test unauthorized access returns 403

## Non-Scope
- Performance testing
- Load testing
- Security penetration testing
- Automated security scanning

## Touchpoints
- `tests/test_tenant_isolation.py` (expand tests)
- `tests/test_permissions.py` (new file)
- `tests/test_web_ui.py` (add permission tests)
- `tests/test_bot_handlers.py` (add permission tests)
- `web/views.py` (add permission checks)
- `bot/handlers.py` (add permission checks)
- `core/middleware.py` (verify tenant scoping)

## UI Notes
- No UI changes (testing only)

## Permission Notes
- Member permissions:
  - View assigned tasks only
  - Edit status/priority/due_date on assigned tasks
  - Cannot edit assignee
  - Cannot access settings
  - Cannot add financial snapshots
  - Read-only access to project KPIs
- Manager permissions:
  - View all tenant tasks/projects
  - Edit all fields on all tasks
  - Access and modify settings
  - Add/edit financial snapshots
  - Invite users

## Acceptance Criteria
- [ ] Tenant isolation tests pass (no cross-tenant visibility)
- [ ] RBAC tests pass for each role
- [ ] Inline edit endpoints protected (403 for unauthorized)
- [ ] Settings endpoint protected (403 for members)
- [ ] Financial snapshot endpoints protected
- [ ] Bot API endpoints protected
- [ ] All queries use tenant filter
- [ ] Test coverage > 90% for permission-related code

## Verification
- Run full test suite: `pytest tests/ -v`
- Manual test: create 2 tenants, verify isolation
- Manual test: login as member, try to access settings → 403
- Manual test: member tries to edit other user's task → 403
- Check coverage: `pytest --cov=. --cov-report=html`

## Risks
- Existing code may have permission gaps
- Bot endpoints may not have consistent permission checks
- Middleware may not catch all cases
- Tests may be slow if creating many fixtures
