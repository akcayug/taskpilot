# TASK-02: Dashboard DataTables Inline Edit

## Goal
Add inline editing capabilities to dashboard with proper column ordering and conflict handling.

## Scope
- Reorder columns: Project → Assignee → Title → Status → Due → Priority → Updated → Actions
- Inline edit fields: status, priority, due_date, assignee (manager only), title (max 100 chars)
- Description editable only in detail page
- Conflict handling with version check or safe update
- Audit log for all changes

## Non-Scope
- Bulk edit
- Multi-row selection
- Excel-like cell navigation
- Description inline edit

## Touchpoints
- `web/templates/dashboard.html`
- `static/js/dashboard.js`
- `web/views.py` (add inline edit endpoint)
- `web/urls.py`
- `tasks/services.py` (update logic with conflict check)
- `audit/signals.py` (ensure audit logging)

## UI Notes
- Double-click or edit icon to enable inline edit
- Input fields replace static text
- Save/Cancel buttons per row or auto-save on blur
- Loading spinner during save
- Error messages inline (e.g., "Task updated by another user")

## Permission Notes
- Manager: can edit all fields on all tasks
- Member: can edit status, priority, due_date, title on assigned tasks only
- Member cannot edit assignee field
- Return 403 if unauthorized

## Acceptance Criteria
- [ ] Column order matches spec
- [ ] Inline edit works for allowed fields
- [ ] Title limited to 100 chars
- [ ] Assignee field only editable by manager
- [ ] Conflict handling shows error message
- [ ] Audit log created with before/after values
- [ ] Save endpoint validates permissions

## Verification
- Edit as manager: all fields editable
- Edit as member: restricted fields only
- Concurrent edit test: open same task in 2 tabs, edit simultaneously
- Check audit log: `AuditLog.objects.filter(action='task_updated')`

## Risks
- Conflict detection may require optimistic locking (version field)
- Auto-save vs manual save UX decision
- DataTables reinit after edit may lose state
