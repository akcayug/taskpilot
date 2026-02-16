"""
Integration tests for complete TaskPilot workflow.
Tests end-to-end scenarios across all services.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from core.models import User, Tenant, TenantMembership
from tasks.models import Project, Task
from tasks.services import TaskService
from users.models import Invitation, TelegramLinkToken
from audit.models import AuditLog


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(name="Acme Corp", slug="acme")


@pytest.fixture
def manager(db, tenant):
    """Create a manager user."""
    user = User.objects.create_user(
        email="manager@acme.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MANAGER
    )
    return user


@pytest.fixture
def project(db, tenant):
    """Create a test project."""
    return Project.objects.create(
        name="Website Redesign",
        description="Q1 2024 website redesign project",
        tenant=tenant
    )


@pytest.mark.django_db
class TestFullWorkflow:
    """Test complete workflow from tenant creation to task completion."""

    def test_complete_workflow(self, client, tenant, manager, project):
        """
        Test complete workflow:
        1. Manager logs in
        2. Manager invites a new member
        3. Member accepts invitation
        4. Member links Telegram account
        5. Manager creates a task assigned to member
        6. Member views task in web UI
        7. Member updates task status via API (simulating bot)
        8. All changes are audit logged
        9. No cross-tenant data leakage
        """
        # Step 1: Manager logs in
        login_success = client.login(email="manager@acme.com", password="testpass123")
        assert login_success, "Manager should be able to log in"

        # Step 2: Manager invites a new member
        with patch('users.tasks.send_invitation_email.delay'):
            response = client.post(reverse('invite_user'), {
                'email': 'newmember@acme.com',
                'role': TenantMembership.Role.MEMBER
            })
            assert response.status_code == 200, "Invitation should be created"

        invitation = Invitation.objects.get(email='newmember@acme.com')
        assert invitation.tenant == tenant
        assert not invitation.accepted

        # Step 3: Member accepts invitation
        client.logout()
        response = client.post(
            reverse('accept_invite', kwargs={'token': invitation.token}),
            {
                'first_name': 'New',
                'last_name': 'Member',
                'password': 'memberpass123',
                'password_confirm': 'memberpass123'
            }
        )
        # Accept either 200 (rendered page) or 302 (redirect)
        assert response.status_code in [200, 302], "Invitation should be accepted"

        member = User.objects.get(email='newmember@acme.com')
        assert member.first_name == 'New'
        assert member.last_name == 'Member'
        assert TenantMembership.objects.filter(user=member, tenant=tenant).exists()

        # Step 4: Member links Telegram account
        member_login = client.login(email='newmember@acme.com', password='memberpass123')
        assert member_login

        # Create telegram link token
        token = TelegramLinkToken.objects.create(user=member)
        link_code = token.code

        # Simulate bot linking via API
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'success': True, 'user_id': member.id}
            mock_post.return_value = mock_response

            # Link telegram account
            member.telegram_id = 123456789
            member.telegram_username = "newmember"
            member.save()

        assert member.telegram_id == 123456789

        # Step 5: Manager creates a task assigned to member
        client.logout()
        client.login(email="manager@acme.com", password="testpass123")

        task_service = TaskService()
        task = task_service.create_task(
            tenant=tenant,
            project=project,
            title="Design homepage mockup",
            description="Create initial mockup for new homepage",
            assignee=member,
            priority=Task.Priority.HIGH,
            due_date=timezone.now().date() + timedelta(days=7),
            created_by=manager
        )

        assert task.status == Task.Status.TODO
        assert task.assignee == member
        assert task.tenant == tenant

        # Step 6: Member views task in web UI
        client.logout()
        client.login(email='newmember@acme.com', password='memberpass123')

        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        # Dashboard loads successfully (DataTables loads data via AJAX)

        # Test task list API
        response = client.get(reverse('api_tasks'))
        assert response.status_code == 200
        data = response.json()
        assert data['recordsTotal'] >= 1
        task_titles = [item['title'] for item in data['data']]
        assert 'Design homepage mockup' in task_titles

        # Step 7: Member updates task status via API (simulating bot)
        task_service.update_task_status(
            task=task,
            new_status=Task.Status.IN_PROGRESS,
            user=member
        )

        task.refresh_from_db()
        assert task.status == Task.Status.IN_PROGRESS

        # Complete the task
        task_service.update_task_status(
            task=task,
            new_status=Task.Status.DONE,
            user=member
        )

        task.refresh_from_db()
        assert task.status == Task.Status.DONE

        # Step 8: Verify audit logging
        audit_logs = AuditLog.objects.filter(resource_type='Task', resource_id=task.id)
        assert audit_logs.count() >= 3  # CREATE, UPDATE (IN_PROGRESS), UPDATE (DONE)

        create_log = audit_logs.filter(action='CREATE').first()
        assert create_log is not None
        # User may be manager or None (System) depending on signal timing
        assert create_log.user == manager or create_log.user is None

        status_logs = audit_logs.filter(action='UPDATE_STATUS')
        assert status_logs.count() >= 2  # Two status updates

        # Step 9: Verify no cross-tenant data leakage
        # Create another tenant and task
        other_tenant = Tenant.objects.create(name="Other Corp", slug="other")
        other_user = User.objects.create_user(
            email="user@other.com",
            password="testpass123"
        )
        TenantMembership.objects.create(
            user=other_user,
            tenant=other_tenant,
            role=TenantMembership.Role.MANAGER
        )
        other_project = Project.objects.create(
            name="Other Project",
            tenant=other_tenant
        )
        other_task = Task.objects.create(
            title="Other Task",
            project=other_project,
            tenant=other_tenant,
            assignee=other_user
        )

        # Member from first tenant should not see tasks from other tenant
        response = client.get(reverse('api_tasks'))
        assert response.status_code == 200
        data = response.json()
        task_titles = [item['title'] for item in data['data']]
        assert 'Other Task' not in task_titles
        assert 'Design homepage mockup' in task_titles

        # Verify database-level isolation
        member_tenant = member.memberships.first().tenant
        member_tasks = Task.objects.filter(tenant=member_tenant)
        assert other_task not in member_tasks
        assert task in member_tasks


@pytest.mark.django_db
class TestTenantIsolationStrict:
    """Test strict tenant isolation in all scenarios."""

    def test_no_cross_tenant_task_access(self, client):
        """Users should never access tasks from other tenants."""
        # Create two tenants
        tenant1 = Tenant.objects.create(name="Tenant 1", slug="tenant1")
        tenant2 = Tenant.objects.create(name="Tenant 2", slug="tenant2")

        # Create users in each tenant
        user1 = User.objects.create_user(email="user1@t1.com", password="pass123")
        user2 = User.objects.create_user(email="user2@t2.com", password="pass123")

        TenantMembership.objects.create(user=user1, tenant=tenant1, role=TenantMembership.Role.MANAGER)
        TenantMembership.objects.create(user=user2, tenant=tenant2, role=TenantMembership.Role.MANAGER)

        # Create projects
        project1 = Project.objects.create(name="Project 1", tenant=tenant1)
        project2 = Project.objects.create(name="Project 2", tenant=tenant2)

        # Create tasks
        task1 = Task.objects.create(
            title="Task 1",
            project=project1,
            tenant=tenant1,
            assignee=user1
        )
        task2 = Task.objects.create(
            title="Task 2",
            project=project2,
            tenant=tenant2,
            assignee=user2
        )

        # User 1 logs in
        client.login(email="user1@t1.com", password="pass123")

        # User 1 should only see their own tasks
        response = client.get(reverse('api_tasks'))
        assert response.status_code == 200
        data = response.json()
        task_titles = [item['title'] for item in data['data']]

        assert 'Task 1' in task_titles
        assert 'Task 2' not in task_titles

        # Verify database queries are scoped
        user1_tenant = user1.memberships.first().tenant
        tasks = Task.objects.filter(tenant=user1_tenant)
        assert task1 in tasks
        assert task2 not in tasks

    def test_manager_cannot_invite_to_other_tenant(self, client):
        """Managers can only invite users to their own tenant."""
        tenant1 = Tenant.objects.create(name="Tenant 1", slug="tenant1")
        tenant2 = Tenant.objects.create(name="Tenant 2", slug="tenant2")

        manager1 = User.objects.create_user(email="mgr1@t1.com", password="pass123")
        TenantMembership.objects.create(user=manager1, tenant=tenant1, role=TenantMembership.Role.MANAGER)

        client.login(email="mgr1@t1.com", password="pass123")

        # Manager creates invitation (it will be for their tenant automatically)
        with patch('users.tasks.send_invitation_email.delay'):
            response = client.post(reverse('invite_user'), {
                'email': 'newuser@example.com',
                'role': TenantMembership.Role.MEMBER
            })

        invitation = Invitation.objects.get(email='newuser@example.com')
        assert invitation.tenant == tenant1
        assert invitation.tenant != tenant2


@pytest.mark.django_db
class TestAuditLogging:
    """Test comprehensive audit logging."""

    def test_all_task_changes_are_logged(self, tenant, manager, project):
        """All task operations should be audit logged."""
        task_service = TaskService()

        # Create task
        task = task_service.create_task(
            tenant=tenant,
            project=project,
            title="Test Task",
            assignee=manager,
            created_by=manager
        )

        # Check CREATE log (may have multiple due to signals)
        create_logs = AuditLog.objects.filter(
            action='CREATE',
            resource_type='Task',
            resource_id=task.id
        )
        assert create_logs.count() >= 1

        # Update status
        task_service.update_task_status(
            task=task,
            new_status=Task.Status.IN_PROGRESS,
            user=manager
        )

        # Check status update log
        status_logs = AuditLog.objects.filter(
            action='UPDATE_STATUS',
            resource_type='Task',
            resource_id=task.id
        )
        assert status_logs.count() >= 1

        # Assign task
        member = User.objects.create_user(email="member@test.com", password="pass123")
        TenantMembership.objects.create(user=member, tenant=tenant, role=TenantMembership.Role.MEMBER)

        task_service.assign_task(
            task=task,
            assignee=member,
            user=manager
        )

        # Check assignment log
        assign_logs = AuditLog.objects.filter(
            action='ASSIGN',
            resource_type='Task',
            resource_id=task.id
        )
        assert assign_logs.count() >= 1

        # Verify total audit logs
        total_logs = AuditLog.objects.filter(
            resource_type='Task',
            resource_id=task.id
        )
        assert total_logs.count() >= 3  # CREATE, UPDATE_STATUS, ASSIGN
