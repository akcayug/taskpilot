# TASK-01: Mobile-First UI

## Goal
Implement mobile-first responsive design with dual rendering modes for task list.

## Scope
- Desktop view: DataTables (current implementation, unchanged)
- Mobile view: Single-column card layout
- Responsive breakpoint: 768px (Bootstrap md)
- No code duplication, same backend data

## Non-Scope
- Kanban board
- Real-time updates
- Advanced gestures (swipe, etc.)
- Native mobile app

## Touchpoints
- `web/templates/dashboard.html`
- `static/css/styles.css`
- `static/js/dashboard.js`
- Possibly create `web/templates/components/task_card.html`

## UI Notes
- Mobile cards show: title, status badge, priority color, due date, assignee avatar
- Cards stacked vertically with spacing
- Tap card to view detail
- No horizontal scrolling
- Status/priority color indicators prominent

## Permission Notes
- Manager: sees all tenant tasks (both views)
- Member: sees assigned tasks only (both views)
- Same RBAC applies to mobile and desktop

## Acceptance Criteria
- [ ] Mobile viewport (< 768px) displays card layout
- [ ] Desktop viewport (>= 768px) displays DataTables
- [ ] No horizontal scrolling on mobile
- [ ] Role-based filtering works in both views
- [ ] No duplicated backend queries

## Verification
- Manual viewport test: 375px, 768px, 1024px
- Test with 5+ tasks with varying data
- Verify manager vs member visibility in both views

## Risks
- DataTables may interfere with responsive behavior (solution: conditionally initialize)
- Card layout may need separate template include
