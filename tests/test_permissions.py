"""
Comprehensive permission tests for RBAC and tenant isolation.

Tests cover:
- Manager vs Member role permissions
- Inline task editing permissions
- Settings endpoint (manager-only)
- Financial snapshot endpoints (manager-only)
- Task visibility (members see only assigned tasks)
- Cross-tenant isolation
"""
import pytest
import json
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership, TenantSettings
from tasks.models import Project, Task, ProjectFinancialSnapshot

User = get_user_model()


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def tenant(db):
    """Create test tenant"""
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant")


@pytest.fixture
def other_tenant(db):
    """Create another tenant for cross-tenant testing"""
    return Tenant.objects.create(name="Other Tenant", slug="other-tenant")


@pytest.fixture
def manager(db, tenant):
    """Create manager user"""
    user = User.objects.create_user(
        email="manager@example.com",
        password="testpass123",
        first_name="Manager",
        last_name="User"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MANAGER
    )
    return user


@pytest.fixture
def member(db, tenant):
    """Create member user"""
    user = User.objects.create_user(
        email="member@example.com",
        password="testpass123",
        first_name="Member",
        last_name="User"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def other_member(db, tenant):
    """Create another member in same tenant"""
    user = User.objects.create_user(
        email="other_member@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def external_user(db, other_tenant):
    """Create user in different tenant"""
    user = User.objects.create_user(
        email="external@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=other_tenant,
        role=TenantMembership.Role.MANAGER
    )
    return user


@pytest.fixture
def project(db, tenant):
    """Create test project"""
    return Project.objects.create(
        tenant=tenant,
        name="Test Project",
        description="Test project",
        contract_total_amount=Decimal('100000.00'),
        contract_retention_total=Decimal('10000.00')
    )


@pytest.fixture
def other_project(db, other_tenant):
    """Create project in other tenant"""
    return Project.objects.create(
        tenant=other_tenant,
        name="Other Project",
        description="Other tenant project"
    )


@pytest.fixture
def member_task(db, tenant, project, member):
    """Create task assigned to member"""
    return Task.objects.create(
        tenant=tenant,
        project=project,
        title="Member Task",
        assignee=member,
        status=Task.Status.TODO,
        priority=Task.Priority.MEDIUM
    )


@pytest.fixture
def other_member_task(db, tenant, project, other_member):
    """Create task assigned to other member"""
    return Task.objects.create(
        tenant=tenant,
        project=project,
        title="Other Member Task",
        assignee=other_member,
        status=Task.Status.TODO,
        priority=Task.Priority.HIGH
    )


@pytest.fixture
def unassigned_task(db, tenant, project):
    """Create unassigned task"""
    return Task.objects.create(
        tenant=tenant,
        project=project,
        title="Unassigned Task",
        status=Task.Status.TODO
    )


@pytest.mark.django_db
class TestTaskVisibilityPermissions:
    """Test task visibility based on role"""

    def test_manager_sees_all_tenant_tasks(self, client, manager, member_task, other_member_task, unassigned_task):
        """Managers should see all tasks in their tenant"""
        client.force_login(manager)
        response = client.get(reverse('api_tasks'), {'draw': 1, 'start': 0, 'length': 25})

        data = json.loads(response.content)
        assert len(data['data']) == 3
        assert data['recordsTotal'] == 3

    def test_member_sees_only_assigned_tasks(self, client, member, member_task, other_member_task, unassigned_task):
        """Members should only see tasks assigned to them"""
        client.force_login(member)
        response = client.get(reverse('api_tasks'), {'draw': 1, 'start': 0, 'length': 25})

        data = json.loads(response.content)
        assert len(data['data']) == 1
        assert data['data'][0]['title'] == 'Member Task'
        assert data['recordsTotal'] == 1

    def test_member_cannot_see_other_member_tasks(self, client, member, member_task, other_member_task):
        """Members cannot see tasks assigned to other members"""
        client.force_login(member)
        response = client.get(reverse('api_tasks'), {'draw': 1, 'start': 0, 'length': 25})

        data = json.loads(response.content)
        task_titles = [task['title'] for task in data['data']]
        assert 'Other Member Task' not in task_titles

    def test_member_cannot_see_unassigned_tasks(self, client, member, member_task, unassigned_task):
        """Members cannot see unassigned tasks"""
        client.force_login(member)
        response = client.get(reverse('api_tasks'), {'draw': 1, 'start': 0, 'length': 25})

        data = json.loads(response.content)
        task_titles = [task['title'] for task in data['data']]
        assert 'Unassigned Task' not in task_titles


@pytest.mark.django_db
class TestInlineEditPermissions:
    """Test inline task editing permissions"""

    def test_manager_can_edit_any_task(self, client, manager, member_task):
        """Managers can edit any task in their tenant"""
        client.force_login(manager)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': member_task.id}),
            data=json.dumps({
                'title': 'Updated by Manager',
                'updated_at': member_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_member_can_edit_own_task(self, client, member, member_task):
        """Members can edit their own assigned tasks"""
        client.force_login(member)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': member_task.id}),
            data=json.dumps({
                'status': 'IN_PROGRESS',
                'updated_at': member_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_member_cannot_edit_other_member_task(self, client, member, other_member_task):
        """Members cannot edit tasks assigned to others"""
        client.force_login(member)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': other_member_task.id}),
            data=json.dumps({
                'title': 'Hacked Title',
                'updated_at': other_member_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        assert response.status_code == 403

    def test_member_cannot_edit_unassigned_task(self, client, member, unassigned_task):
        """Members cannot edit unassigned tasks"""
        client.force_login(member)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': unassigned_task.id}),
            data=json.dumps({
                'title': 'Hacked Title',
                'updated_at': unassigned_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        assert response.status_code == 403

    def test_member_cannot_change_assignee(self, client, member, member_task, other_member):
        """Members cannot change task assignee"""
        client.force_login(member)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': member_task.id}),
            data=json.dumps({
                'assignee_id': other_member.id,
                'updated_at': member_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        # Member requests should not include assignee changes
        # Either 403 or ignored, depending on implementation
        data = json.loads(response.content)
        member_task.refresh_from_db()
        assert member_task.assignee == member  # Assignee unchanged

    def test_manager_can_change_assignee(self, client, manager, member_task, other_member):
        """Managers can change task assignee"""
        client.force_login(manager)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': member_task.id}),
            data=json.dumps({
                'assignee_id': other_member.id,
                'updated_at': member_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        member_task.refresh_from_db()
        assert member_task.assignee == other_member


@pytest.mark.django_db
class TestSettingsPermissions:
    """Test settings endpoint permissions (manager-only)"""

    def test_manager_can_access_settings(self, client, manager):
        """Managers can access settings page"""
        client.force_login(manager)
        response = client.get(reverse('settings'))

        assert response.status_code == 200
        assert b'Tenant Settings' in response.content

    def test_member_cannot_access_settings(self, client, member):
        """Members cannot access settings page"""
        client.force_login(member)
        response = client.get(reverse('settings'))

        assert response.status_code == 403
        assert b'Permission denied' in response.content

    def test_manager_can_update_settings(self, client, manager, tenant):
        """Managers can update tenant settings"""
        client.force_login(manager)

        response = client.post(reverse('settings'), {
            'ai_enabled': 'on',
            'ai_system_prompt': 'Test prompt for AI',
            'ai_default_mode': 'fix',
            'ai_default_language': 'en'
        })

        assert response.status_code == 302  # Redirect on success

        # Verify settings were updated
        settings = TenantSettings.objects.get(tenant=tenant)
        assert settings.ai_enabled is True
        assert settings.ai_system_prompt == 'Test prompt for AI'

    def test_member_cannot_update_settings(self, client, member):
        """Members cannot update settings"""
        client.force_login(member)

        response = client.post(reverse('settings'), {
            'ai_enabled': 'on',
            'ai_system_prompt': 'Hacked prompt',
            'ai_default_mode': 'fix',
            'ai_default_language': 'en'
        })

        assert response.status_code == 403


@pytest.mark.django_db
class TestFinancialSnapshotPermissions:
    """Test financial snapshot permissions (manager-only)"""

    def test_manager_can_view_project_financials(self, client, manager, project):
        """Managers can view project financial KPIs"""
        client.force_login(manager)
        response = client.get(reverse('project_detail', kwargs={'project_id': project.id}))

        assert response.status_code == 200
        assert b'Financial KPIs' in response.content
        assert b'Create New Financial Snapshot' in response.content

    def test_member_can_view_project_financials(self, client, member, project):
        """Members can view project financial KPIs (read-only)"""
        client.force_login(member)
        response = client.get(reverse('project_detail', kwargs={'project_id': project.id}))

        assert response.status_code == 200
        assert b'Financial KPIs' in response.content
        # Member should not see snapshot creation form
        assert b'Create New Financial Snapshot' not in response.content

    def test_manager_can_create_snapshot(self, client, manager, project):
        """Managers can create financial snapshots"""
        client.force_login(manager)

        response = client.post(
            reverse('snapshot_create', kwargs={'project_id': project.id}),
            {
                'total_completed_work': '50000.00',
                'total_paid_amount': '40000.00',
                'total_retention_earned': '5000.00',
                'notes': 'Monthly snapshot'
            }
        )

        assert response.status_code == 302  # Redirect on success

        # Verify snapshot was created
        snapshot = ProjectFinancialSnapshot.objects.get(project=project)
        assert snapshot.total_completed_work == Decimal('50000.00')
        assert snapshot.created_by == manager

    def test_member_cannot_create_snapshot(self, client, member, project):
        """Members cannot create financial snapshots"""
        client.force_login(member)

        response = client.post(
            reverse('snapshot_create', kwargs={'project_id': project.id}),
            {
                'total_completed_work': '50000.00',
                'total_paid_amount': '40000.00',
                'total_retention_earned': '5000.00',
                'notes': 'Unauthorized snapshot'
            }
        )

        assert response.status_code == 403

        # Verify no snapshot was created
        assert not ProjectFinancialSnapshot.objects.filter(project=project).exists()

    def test_snapshot_validation_prevents_exceeding_contract(self, client, manager, project):
        """Snapshot validation prevents completed work exceeding contract total"""
        client.force_login(manager)

        response = client.post(
            reverse('snapshot_create', kwargs={'project_id': project.id}),
            {
                'total_completed_work': '150000.00',  # Exceeds contract_total_amount
                'total_paid_amount': '40000.00',
                'total_retention_earned': '5000.00'
            }
        )

        # Should redirect back with error
        assert response.status_code == 302
        assert not ProjectFinancialSnapshot.objects.filter(project=project).exists()


@pytest.mark.django_db
class TestCrossTenantIsolation:
    """Test that users cannot access data from other tenants"""

    def test_user_cannot_view_other_tenant_project(self, client, member, other_project):
        """Users cannot view projects from other tenants"""
        client.force_login(member)

        response = client.get(reverse('project_detail', kwargs={'project_id': other_project.id}))

        # Should return 404 (tenant filter prevents finding the project)
        assert response.status_code == 404

    def test_user_cannot_edit_other_tenant_task(self, client, member, other_project):
        """Users cannot edit tasks from other tenants"""
        # Create task in other tenant
        other_task = Task.objects.create(
            tenant=other_project.tenant,
            project=other_project,
            title="Other Tenant Task",
            status=Task.Status.TODO
        )

        client.force_login(member)

        response = client.patch(
            reverse('task_inline_update', kwargs={'task_id': other_task.id}),
            data=json.dumps({
                'title': 'Hacked',
                'updated_at': other_task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }),
            content_type='application/json'
        )

        # Should return 403 or 404
        assert response.status_code in [403, 404]

    def test_user_cannot_create_snapshot_for_other_tenant(self, client, manager, other_project):
        """Users cannot create snapshots for projects in other tenants"""
        client.force_login(manager)

        response = client.post(
            reverse('snapshot_create', kwargs={'project_id': other_project.id}),
            {
                'total_completed_work': '50000.00',
                'total_paid_amount': '40000.00',
                'total_retention_earned': '5000.00'
            }
        )

        # Should return 404 (tenant filter prevents finding the project)
        assert response.status_code == 404

        # Verify no snapshot was created
        assert not ProjectFinancialSnapshot.objects.filter(project=other_project).exists()

    def test_task_api_filters_by_tenant(self, client, member, member_task, other_project):
        """Task API should automatically filter by tenant"""
        # Create task in other tenant
        Task.objects.create(
            tenant=other_project.tenant,
            project=other_project,
            title="Other Tenant Task"
        )

        client.force_login(member)
        response = client.get(reverse('api_tasks'), {'draw': 1, 'start': 0, 'length': 25})

        data = json.loads(response.content)
        # Should only see task from own tenant
        assert len(data['data']) == 1
        assert data['data'][0]['title'] == 'Member Task'


@pytest.mark.django_db
class TestDashboardStatisticsPermissions:
    """Test dashboard statistics respect RBAC"""

    def test_manager_statistics_include_all_tasks(self, client, manager, member_task, other_member_task, unassigned_task):
        """Manager dashboard statistics include all tenant tasks"""
        client.force_login(manager)
        response = client.get(reverse('dashboard'))

        assert response.status_code == 200
        assert response.context['total_tasks'] == 3

    def test_member_statistics_include_only_assigned(self, client, member, member_task, other_member_task, unassigned_task):
        """Member dashboard statistics include only assigned tasks"""
        client.force_login(member)
        response = client.get(reverse('dashboard'))

        assert response.status_code == 200
        assert response.context['total_tasks'] == 1


@pytest.mark.django_db
class TestExportPermissions:
    """Test CSV export respects RBAC"""

    def test_manager_export_includes_all_tasks(self, client, manager, member_task, other_member_task):
        """Manager export includes all tenant tasks"""
        client.force_login(manager)
        response = client.get(reverse('export_tasks'))

        content = response.content.decode('utf-8')
        assert 'Member Task' in content
        assert 'Other Member Task' in content

    def test_member_export_includes_only_assigned(self, client, member, member_task, other_member_task):
        """Member export includes only assigned tasks"""
        client.force_login(member)
        response = client.get(reverse('export_tasks'))

        content = response.content.decode('utf-8')
        assert 'Member Task' in content
        assert 'Other Member Task' not in content
