# TaskPilot Smoke Test Guide

## Pre-requisites

### Environment Variables
Ensure `.env` file is configured with:
```bash
# Database
DB_NAME=taskpilot
DB_USER=taskpilot
DB_PASSWORD=<secure_password>

# Django
SECRET_KEY=<django_secret_key>
DEBUG=False
ALLOWED_HOSTS=*

# Telegram
TELEGRAM_BOT_TOKEN=<your_bot_token>

# OpenAI (for AI features)
OPENAI_API_KEY=<your_openai_key>

# Web URL
WEB_URL=http://web:8000
```

### Required Tools
- Docker & Docker Compose
- curl (for healthz checks)
- Web browser (Chrome/Firefox)
- Telegram app (for bot testing)

## 1. Service Health Checks

### Start Services
```bash
docker-compose up -d
```

### Verify Services Running
```bash
docker-compose ps
```

Expected output: All services should show "Up" and "healthy" status:
- db
- redis
- web
- bot
- worker

### Check Healthz Endpoints

**Web Service:**
```bash
curl http://localhost:8000/healthz
```
Expected: `{"status": "healthy", "database": "connected"}`

**Bot Service:**
```bash
curl http://localhost:8001/healthz
```
Expected: `{"status": "healthy", "service": "telegram-bot"}`

**Worker Service:**
```bash
curl http://localhost:8002/healthz
```
Expected: `{"status": "healthy", "service": "worker"}`

### Check Logs for Errors
```bash
docker-compose logs | grep -i error
```
Expected: No critical errors (some warnings are acceptable)

**Individual service logs:**
```bash
docker-compose logs web
docker-compose logs bot
docker-compose logs worker
```

## 2. Data Setup

### Access Django Admin
1. Navigate to `http://localhost:8000/admin/`
2. Create superuser if needed:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Create Test Data via Django Shell
```bash
docker-compose exec web python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership
from tasks.models import Project, Task
from decimal import Decimal

User = get_user_model()

# Create tenant
tenant = Tenant.objects.create(name="Test Company", slug="test-company")

# Create manager user
manager = User.objects.create_user(
    email="manager@test.com",
    password="testpass123",
    first_name="Manager",
    last_name="User"
)
TenantMembership.objects.create(
    user=manager,
    tenant=tenant,
    role=TenantMembership.Role.MANAGER
)

# Create member user
member = User.objects.create_user(
    email="member@test.com",
    password="testpass123",
    first_name="Member",
    last_name="User"
)
TenantMembership.objects.create(
    user=member,
    tenant=tenant,
    role=TenantMembership.Role.MEMBER
)

# Create projects
project1 = Project.objects.create(
    tenant=tenant,
    name="Website Redesign",
    description="Company website redesign project",
    contract_total_amount=Decimal('100000.00'),
    contract_retention_total=Decimal('10000.00')
)

project2 = Project.objects.create(
    tenant=tenant,
    name="Mobile App",
    description="Mobile application development",
    contract_total_amount=Decimal('200000.00'),
    contract_retention_total=Decimal('20000.00')
)

# Create tasks
Task.objects.create(
    tenant=tenant,
    project=project1,
    title="Design homepage mockup",
    description="Create homepage design in Figma",
    assignee=member,
    status=Task.Status.TODO,
    priority=Task.Priority.HIGH
)

Task.objects.create(
    tenant=tenant,
    project=project1,
    title="Implement responsive layout",
    assignee=member,
    status=Task.Status.IN_PROGRESS,
    priority=Task.Priority.MEDIUM
)

Task.objects.create(
    tenant=tenant,
    project=project1,
    title="Setup CI/CD pipeline",
    status=Task.Status.TODO,
    priority=Task.Priority.LOW
)

Task.objects.create(
    tenant=tenant,
    project=project2,
    title="Design app UI/UX",
    assignee=manager,
    status=Task.Status.DONE,
    priority=Task.Priority.HIGH
)

Task.objects.create(
    tenant=tenant,
    project=project2,
    title="Develop authentication flow",
    assignee=member,
    status=Task.Status.IN_PROGRESS,
    priority=Task.Priority.HIGH
)

print("✅ Test data created successfully!")
print(f"Manager: manager@test.com / testpass123")
print(f"Member: member@test.com / testpass123")
```

## 3. Web UI Testing (Desktop)

### Login Tests
- [ ] Navigate to `http://localhost:8000/`
- [ ] Redirects to login page
- [ ] Login as manager (manager@test.com / testpass123)
- [ ] Redirects to dashboard

### Dashboard - Manager View
- [ ] Dashboard loads successfully
- [ ] Statistics cards show: Total Tasks, To Do, In Progress, Done
- [ ] DataTables displays with all tasks visible
- [ ] Filter dropdowns work (Status, Priority, Assignee)
- [ ] Search box filters tasks
- [ ] Export CSV button works

### Inline Edit - Manager
- [ ] Click "Edit" on any task
- [ ] Row turns yellow (editing mode)
- [ ] All fields become editable
- [ ] Can change: Title, Status, Priority, Due Date, Assignee
- [ ] Click "Save" - changes persist
- [ ] Click "Cancel" - reverts changes
- [ ] Try editing same task in two tabs - conflict detection shows warning

### Project Detail - Manager
- [ ] Click on project name in task list
- [ ] Project detail page loads with KPI cards
- [ ] Shows: Completion %, Remaining Work, Payment Status, etc.
- [ ] "Create New Financial Snapshot" form visible
- [ ] Fill in snapshot data and submit
- [ ] Snapshot appears in history table

### Settings - Manager
- [ ] Click "Settings" in navbar
- [ ] Settings page loads
- [ ] Can toggle "Enable AI Features"
- [ ] Can edit AI system prompt
- [ ] Can change default mode and language
- [ ] Save settings - success message appears

### Logout & Login as Member
- [ ] Logout from manager account
- [ ] Login as member (member@test.com / testpass123)

### Dashboard - Member View
- [ ] Dashboard shows only assigned tasks (not all tenant tasks)
- [ ] Statistics reflect only assigned tasks
- [ ] Cannot see unassigned tasks
- [ ] Cannot see tasks assigned to manager

### Inline Edit - Member
- [ ] Can edit own assigned tasks
- [ ] Click "Edit" on assigned task - works
- [ ] Can change: Title, Status, Priority, Due Date
- [ ] Assignee field is read-only or hidden
- [ ] Try to edit unassigned task - should fail or not show edit button

### Settings - Member
- [ ] "Settings" link not visible in navbar (or)
- [ ] Navigate to `/settings/` manually
- [ ] Should get 403 Forbidden error

### Project Detail - Member
- [ ] Click on project name
- [ ] Can view KPI cards (read-only)
- [ ] "Create New Financial Snapshot" form NOT visible
- [ ] Try POST to snapshot creation endpoint - should get 403

## 4. Web UI Testing (Mobile)

### Resize Browser
- [ ] Open DevTools (F12)
- [ ] Toggle device toolbar (Ctrl+Shift+M)
- [ ] Select iPhone or Android device (< 768px width)

### Mobile View
- [ ] Dashboard shows card layout (not DataTables)
- [ ] No horizontal scrolling
- [ ] Each task shows as a card with:
  - Title
  - Project name (clickable)
  - Assignee
  - Due date
  - Status and priority badges
- [ ] Cards have colored left border based on priority
- [ ] Pagination buttons work (Previous/Next)
- [ ] Filters still work in mobile view

## 5. AI Helper Testing

### Navigate to AI Demo
- [ ] Click "AI Demo" in navbar
- [ ] AI demo page loads

### Test "Fix Language"
- [ ] Enter text with grammar errors: "I has many task to do today"
- [ ] Click "Fix Language"
- [ ] Loading spinner appears
- [ ] Modal shows with original vs suggested text
- [ ] Suggested text has corrections: "I have many tasks to do today"
- [ ] Click "Apply" - form field updates

### Test "Translate"
- [ ] Enter English text: "Complete the project by Friday"
- [ ] Click "Translate"
- [ ] Modal shows translation (based on tenant settings language)
- [ ] Click "Apply" - form field updates

### Verify AI Settings
- [ ] Go to Settings page (as manager)
- [ ] Change AI default language to Turkish (tr)
- [ ] Save settings
- [ ] Go back to AI Demo
- [ ] Test translate - should now translate to Turkish

## 6. Telegram Bot Testing

### Link Telegram Account
1. Open Telegram app
2. Search for your bot (@YourBotUsername)
3. Send `/start` command
4. Bot responds with welcome message and link instructions

### Get Link Code
1. In web UI, navigate to link page (if implemented) or
2. Use Django shell:
   ```python
   from core.models import User
   user = User.objects.get(email='member@test.com')
   print(f"Link code: {user.telegram_link_code}")
   ```

### Link Account
- [ ] Send `/link <code>` to bot
- [ ] Bot confirms successful linking

### Test Commands
**Manager User:**
- [ ] `/tasks` - shows all tenant tasks
- [ ] `/tasks todo` - filters by status
- [ ] `/task 1` - shows specific task details
- [ ] Can see tasks assigned to others

**Member User:**
- [ ] `/tasks` - shows only assigned tasks
- [ ] Cannot see unassigned or other member tasks
- [ ] `/task 1` - can view details of assigned task
- [ ] Try to view other's task - get "not found" error

### Task Creation
- [ ] Send `/newtask` or `/add`
- [ ] Bot shows project selection
- [ ] Select project
- [ ] Enter task title
- [ ] Enter description (or skip)
- [ ] Select priority
- [ ] Enter due date or skip
- [ ] Bot confirms task creation
- [ ] Verify task appears in web UI

### Voice Message (if AI enabled)
- [ ] Send voice message to bot
- [ ] Bot transcribes using Whisper API
- [ ] Bot shows transcription and AI-improved version
- [ ] Confirm to create task
- [ ] Task created with improved text

## 7. Permission Verification

### Cross-Tenant Isolation
1. Create second tenant with users:
   ```python
   tenant2 = Tenant.objects.create(name="Other Company", slug="other-company")
   user2 = User.objects.create_user(email="user2@other.com", password="test123")
   TenantMembership.objects.create(user=user2, tenant=tenant2, role='MEMBER')
   ```

2. Login as user2
- [ ] Cannot see tenant1's tasks
- [ ] Cannot access tenant1's projects
- [ ] Dashboard shows 0 tasks

### Member Restrictions
Login as member:
- [ ] Navigate to `/settings/` → 403 Forbidden
- [ ] Try to edit other member's task via API:
  ```bash
  curl -X PATCH http://localhost:8000/api/tasks/3/ \
    -H "Cookie: sessionid=<session_cookie>" \
    -H "Content-Type: application/json" \
    -d '{"title": "Hacked"}'
  ```
  Expected: 403 Forbidden

- [ ] Try to create financial snapshot:
  ```bash
  curl -X POST http://localhost:8000/projects/1/snapshots/create/ \
    -H "Cookie: sessionid=<session_cookie>" \
    -d "total_completed_work=50000&..."
  ```
  Expected: 403 Forbidden

## 8. Log Review

### Check for Errors
```bash
# All services
docker-compose logs | grep -i "error" | grep -v "0 errors"

# Web service only
docker-compose logs web | grep -i "error"

# Bot service
docker-compose logs bot | grep -i "error"

# Worker service
docker-compose logs worker | grep -i "error"
```

Expected: No critical errors. Some acceptable warnings:
- Static file warnings (if not collected)
- Migration warnings (if already applied)

### Check Browser Console
- [ ] Open DevTools (F12) → Console tab
- [ ] Navigate through all pages
- [ ] No JavaScript errors (red messages)
- [ ] No failed API requests (check Network tab)

## 9. Final Checks

### Database State
```bash
docker-compose exec web python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership
from tasks.models import Project, Task, ProjectFinancialSnapshot

# Verify data counts
print(f"Tenants: {Tenant.objects.count()}")
print(f"Users: {get_user_model().objects.count()}")
print(f"Projects: {Project.objects.count()}")
print(f"Tasks: {Task.objects.count()}")
print(f"Snapshots: {ProjectFinancialSnapshot.objects.count()}")

# Check tenant isolation
for tenant in Tenant.objects.all():
    print(f"\n{tenant.name}:")
    print(f"  Projects: {Project.objects.filter(tenant=tenant).count()}")
    print(f"  Tasks: {Task.objects.filter(tenant=tenant).count()}")
```

### Git Status
```bash
git status
```
Expected: Clean working directory (all changes committed)

```bash
git log --oneline -10
```
Verify all TASK commits are present

## 10. Post-Smoke Test

### Stop Services
```bash
docker-compose down
```

### Archive Test Data (Optional)
```bash
docker-compose exec db pg_dump -U taskpilot taskpilot > backup.sql
```

### Tag Release
```bash
git tag -a v1.0.0 -m "Release v1.0.0 - All tasks complete"
git push origin v1.0.0
```

## Smoke Test Summary

| Category | Items | Passed | Failed |
|----------|-------|--------|--------|
| Services | 5 | __ | __ |
| Healthz | 3 | __ | __ |
| Web UI (Desktop) | 12 | __ | __ |
| Web UI (Mobile) | 6 | __ | __ |
| AI Helper | 5 | __ | __ |
| Bot Commands | 8 | __ | __ |
| Permissions | 6 | __ | __ |
| Logs | 2 | __ | __ |
| **TOTAL** | **47** | **__** | **__** |

---

**Test Completed By:** _______________
**Date:** _______________
**Environment:** Local Docker Compose
**Version:** v1.0.0

## Notes

Record any issues found during testing:
-
-
-

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues found
- [ ] Logs reviewed - no critical errors
- [ ] Ready for deployment

**Approved By:** _______________
**Date:** _______________
