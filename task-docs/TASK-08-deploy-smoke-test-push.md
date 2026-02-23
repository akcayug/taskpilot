# TASK-08: Deploy Smoke Test + Push

## Goal
Final validation with comprehensive smoke testing before deployment.

## Scope
- Start all services with docker-compose
- Verify all healthz endpoints
- Create test data (tenant, users, projects, tasks)
- Manual smoke test checklist covering all features
- Review logs for errors
- Commit and push to main

## Non-Scope
- Automated end-to-end tests (manual checklist only)
- Production deployment (local validation only)
- Performance benchmarking
- Security audit

## Touchpoints
- All code
- `docker-compose.yml`
- `.env`

## Smoke Test Checklist
1. Services:
   - [ ] `docker-compose up -d` succeeds
   - [ ] All services show "healthy" in `docker-compose ps`
   - [ ] Web /healthz returns 200
   - [ ] Bot /healthz returns 200
   - [ ] Worker /healthz returns 200

2. Data setup:
   - [ ] Create tenant via Django admin
   - [ ] Create manager user
   - [ ] Create member user
   - [ ] Create 2 projects
   - [ ] Create 5+ tasks

3. Web UI (Desktop):
   - [ ] Dashboard shows DataTables
   - [ ] Inline edit works (manager)
   - [ ] Inline edit restricted (member)
   - [ ] Settings page accessible (manager only)
   - [ ] Project KPIs display correctly
   - [ ] Financial snapshot can be added

4. Web UI (Mobile):
   - [ ] Dashboard shows card layout (< 768px)
   - [ ] No horizontal scrolling
   - [ ] Cards show correct data

5. Web AI Helper:
   - [ ] "Fix language" shows suggestion
   - [ ] "Translate" shows translation
   - [ ] Apply updates form field

6. Bot:
   - [ ] /start works
   - [ ] /tasks shows filtered list
   - [ ] /add creates task
   - [ ] Voice message → transcription → suggestion → confirm
   - [ ] Manager sees all tasks, member sees assigned only

7. Logs:
   - [ ] No ERROR in `docker-compose logs`
   - [ ] No browser console errors

8. Permissions:
   - [ ] Member cannot access settings (403)
   - [ ] Member cannot edit other user's tasks
   - [ ] No cross-tenant data visible

## Acceptance Criteria
- [ ] Smoke test checklist 100% complete
- [ ] All services healthy
- [ ] No errors in logs
- [ ] Git status clean after commit

## Verification
- Execute checklist line by line
- Screenshot evidence for key features
- Review logs: `docker-compose logs | grep ERROR`
- Browser console: F12, check for errors
- Git: `git status`, `git log`, `git push`

## Risks
- Smoke test may reveal late-stage bugs
- Docker compose may fail on first run (env vars)
- API keys may be missing (OpenAI)
- Time-consuming manual testing
