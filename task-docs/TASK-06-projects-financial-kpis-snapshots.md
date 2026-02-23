# TASK-06: Projects Financial KPIs + Snapshots

## Goal
Add financial tracking to projects with KPIs, progress bars, and snapshot history.

## Scope
- Extend Project model with contract and financial fields
- Store user-input values: completed work, paid amount, retention earned
- Compute derived KPIs (NOT stored): completion %, remaining work, paid %, etc.
- UI with KPI cards and progress bars
- Snapshot model for historical tracking
- Form to add new snapshot entry

## Non-Scope
- Automated snapshot creation (manual entry only)
- Budget forecasting or predictive analytics
- Multi-currency support
- Invoice generation
- Export to accounting software

## Touchpoints
- `tasks/models.py` (add fields to Project, create ProjectFinancialSnapshot model)
- `tasks/migrations/` (create migration)
- `web/templates/project_detail.html` (add KPI section)
- `web/views.py` (ProjectDetailView, SnapshotCreateView)
- `web/urls.py`
- `static/css/styles.css` (KPI card styles, progress bars)

## UI Notes
- KPI cards layout: 3 columns (work, payment, retention)
- Each card shows: label, value, progress bar, percentage
- Progress bars: green fill, percentage label
- Snapshot history table: Date | Completed | Paid | Retention Earned | Actions
- "Add Snapshot" button opens form

## Permission Notes
- Manager: can view and add snapshots
- Member: can view snapshots (read-only)
- No inline editing of snapshots (create only)

## Acceptance Criteria
- [ ] Project model has: contract_total_amount, contract_retention_total
- [ ] Snapshot model has: completed, paid, retention_earned, timestamp
- [ ] Derived fields computed correctly (verify math manually)
- [ ] KPI cards display correct values
- [ ] Progress bars reflect correct percentages
- [ ] Snapshot history shows entries in chronological order
- [ ] Manager can add snapshot, member cannot
- [ ] Validation: no negative values, completed <= contract_total

## Verification
- Enter test values:
  - contract_total = 100,000
  - contract_retention = 10,000
  - completed = 50,000
  - paid = 40,000
  - retention_earned = 5,000
- Verify computed values:
  - completion_percentage = 50%
  - remaining_work = 50,000
  - paid_percentage = 44.44%
  - remaining_payment = 50,000
  - remaining_retention = 5,000
- Create snapshot, verify appears in history

## Risks
- Division by zero if contract_total = 0 (validation required)
- Rounding errors in percentage calculations
- Snapshot history may grow large (pagination needed)
- Field names may be unclear (use help text)
