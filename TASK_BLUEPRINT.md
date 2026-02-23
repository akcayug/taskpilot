# Task Blueprint - Authoritative Task Definitions

## TASK-01: mobile-first-ui

**Goal**: Mobile-first redesign with dual rendering modes

**Requirements**:
- Desktop: DataTables view (unchanged behavior)
- Mobile: single-column card layout (no horizontal scroll tables)
- Same backend logic, no duplicated business logic
- Clean breakpoint strategy (template or responsive layer)
- Responsive breakpoint: 768px (Bootstrap md breakpoint)

**Acceptance**:
- Mobile viewport shows card layout
- Desktop viewport shows DataTables
- Permissions unchanged (Manager sees all, Member sees assigned only)
- No horizontal scrolling on mobile

**Verification**:
- Manual viewport test at 375px, 768px, 1024px widths
- Role-based visibility confirmed for both views
- Test with real tasks (5+ tasks with varying data)

---

## TASK-02: dashboard-datatables-inline-edit

**Goal**: Refine dashboard UX with inline editing capabilities

**Requirements**:
- Column order: Project → Assignee → Title → Status → Due → Priority → Updated → Actions
- Inline edit allowed only for: status, priority, due_date, assignee (manager only), title (short text, max 100 chars)
- Description only editable in detail page (not inline)
- Conflict handling: version check or safe update with error message
- Audit entry on every change
- Save button per row or auto-save on blur
- Cancel/revert option

**Acceptance**:
- RBAC enforced (Manager edits all fields, Member edits limited fields on assigned tasks)
- Inline edits validated (required fields, valid dates, valid status transitions)
- Conflict case handled gracefully (e.g., "Task updated by another user, please refresh")
- Audit log created with before/after values

**Verification**:
- Edit test for manager role (all fields)
- Edit test for member role (restricted fields)
- Concurrent edit test (simulate conflict)
- Audit log query shows change entries

---

## TASK-03: tenant-settings-manager-admin

**Goal**: Per-tenant manager-admin settings UI (NOT Django admin)

**Requirements**:
- Visible only to manager role
- Settings stored per tenant:
  - AI enabled (boolean toggle)
  - AI system prompt (text field, max 500 chars)
  - Default mode: "fix" or "translate" (dropdown)
  - Default target language (dropdown: en, tr, de, fr, es)
- Stored per tenant (TenantSettings model or JSON field on Tenant)
- Settings used by AI flows in later tasks
- Web-based form at /settings URL
- Form validation (required fields, max lengths)

**Acceptance**:
- Manager updates persist to database
- Member cannot access /settings (403 Forbidden)
- Settings load correctly on page reload
- Default values set for new tenants

**Verification**:
- Permission check: member user gets 403
- Save/load test: update values, reload page, verify persistence
- Validation test: submit empty/invalid values, verify errors

---

## TASK-04: telegram-bot-tasks-projects-filters

**Goal**: Enhance bot flows with LLM + speech support

**Requirements**:
- `/tasks` command with filters:
  - Filter by status (TODO/IN_PROGRESS/DONE)
  - Filter by project (list of tenant projects)
- `/add` command for interactive task creation flow
- Voice message support:
  - Accept voice messages in any task creation flow
  - Transcribe audio using speech-to-text API (OpenAI Whisper or similar)
  - Pass transcript to LLM API (OpenAI GPT-4 or similar)
  - LLM reformulates clean task text using tenant system prompt
  - Optionally translate to tenant default language if set
- LLM output is suggestion-only
- User sees suggestion and must confirm before task is created
- Respect tenant context + RBAC
- If user belongs to multiple tenants → active tenant selection step

**Acceptance**:
- Member sees own tasks only (filtered by assignee)
- Manager sees all tenant tasks
- Voice input → transcript → LLM clean output → user confirms → task created
- No automatic overwrite or creation without confirmation
- Multi-tenant users can select active tenant

**Verification**:
- Manual bot flow test with voice message
- Role tests: member vs manager task visibility
- Multi-tenant test: user in 2 tenants selects correct one
- LLM suggestion test: voice input produces cleaned text

---

## TASK-05: ai-helper-web-task-create-edit

**Goal**: LLM integration in web task create/edit forms

**Requirements**:
- On task create/edit page add buttons:
  - "Fix language" button
  - "Translate" button
- Use tenant AI system prompt + default target language from TenantSettings
- Call external LLM API (OpenAI GPT-4 or similar)
- Suggestion-only: show before/after diff
- User must click "Apply" to update form fields
- Log before/after in audit log
- Button states: loading spinner during API call
- Error handling: API timeout, API error

**Acceptance**:
- Suggestion visible in modal or side-by-side view
- Apply button updates task form fields
- Audit entry exists with action type "ai_suggestion_applied"
- Works on both create and edit pages

**Verification**:
- Manual create/edit test with "Fix language"
- Manual test with "Translate"
- Verify audit log entry
- Test error handling (disconnect API, verify error message)

---

## TASK-06: projects-financial-kpis-snapshots

**Goal**: Clear financial state overview with KPI tracking

**Requirements**:
- Project model must include:
  - contract_total_amount (decimal, required)
  - contract_retention_total (decimal, required)
- User inputs (stored fields):
  - total_completed_work (decimal)
  - total_paid_amount (decimal)
  - total_retention_earned (decimal)
- Derived fields (computed in view/template, NOT stored):
  - completion_percentage = (completed / contract_total) * 100
  - remaining_work = contract_total - completed
  - paid_percentage = (paid / (contract_total - contract_retention_total)) * 100
  - remaining_payment = (contract_total - contract_retention_total) - paid
  - remaining_retention = contract_retention_total - retention_earned
- UI displays:
  - KPI cards with labeled values
  - Progress bars for: work progress, payment progress, retention earned progress
  - Snapshot history table (chronological, show date + values)
- Snapshot model: ProjectFinancialSnapshot with timestamp + values
- Form to add new snapshot entry

**Acceptance**:
- Computed fields correct (verify math manually)
- No duplicated stored derived fields
- Progress bars reflect correct percentages
- Snapshot history shows entries in chronological order

**Verification**:
- Enter sample values → validate calculations
- Create snapshot → verify appears in history
- Test edge cases: 0 values, 100% completion, negative values (should validate)

---

## TASK-07: permissions-tests-hardening

**Goal**: Ensure strict tenant isolation + RBAC across web & bot

**Requirements**:
- Every query tenant-scoped (no cross-tenant data leakage)
- Member permissions:
  - View assigned tasks only
  - Edit status/priority on assigned tasks only
  - Cannot view other users' tasks
  - Cannot access tenant settings
- Manager permissions:
  - View all tenant tasks/projects
  - Edit all fields on all tasks
  - Access tenant settings
  - Invite users
- Inline edit endpoints protected with permission checks
- Bot API endpoints protected with tenant + role checks
- Add/update tests:
  - Tenant isolation tests (create 2 tenants, verify no cross-tenant visibility)
  - RBAC tests for each role
  - Endpoint permission tests (web + bot)

**Acceptance**:
- No cross-tenant visibility in any scenario
- All role rules enforced (member/manager)
- Unauthorized access returns 403 Forbidden
- Test suite passes with 100% permission coverage

**Verification**:
- Run full test suite: `pytest tests/`
- Manual test: create 2 tenants, verify isolation
- Manual test: member cannot edit manager-only fields

---

## TASK-08: deploy-smoke-test-push

**Goal**: Final validation + deployment

**Requirements**:
- `docker-compose up -d` starts all services
- All `/healthz` endpoints return 200 OK
- Create test data:
  - 1 tenant
  - 1 manager user
  - 1 member user
  - 2 projects
  - 5+ tasks
- Validate:
  - Desktop + mobile dashboard rendering
  - DataTables inline edit (desktop)
  - Card view (mobile)
  - Bot task create/list
  - Voice → transcript → LLM flow (bot)
  - Web AI helper (fix language / translate)
  - Project KPIs display correctly
  - Tenant settings save/load
  - Permission isolation (manager vs member)
- Only after smoke test passes: commit & push to main

**Acceptance**:
- Smoke test checklist completed
- All services healthy
- No console errors in browser
- No errors in docker-compose logs

**Verification**:
- Manual smoke test checklist execution
- Review logs: `docker-compose logs | grep ERROR`
- Browser console: no errors
- Git status clean after commit
