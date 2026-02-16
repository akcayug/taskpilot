import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership
from tasks.models import Project, Task

User = get_user_model()


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def tenant(db):
    """Create a test tenant"""
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant")


@pytest.fixture
def other_tenant(db):
    """Create another tenant for isolation testing"""
    return Tenant.objects.create(name="Other Tenant", slug="other-tenant")


@pytest.fixture
def user(db, tenant):
    """Create a user in the test tenant"""
    user = User.objects.create_user(
        email="user@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def other_user(db, other_tenant):
    """Create a user in a different tenant"""
    user = User.objects.create_user(
        email="other@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=other_tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def project(db, tenant):
    """Create a test project"""
    return Project.objects.create(
        tenant=tenant,
        name="Test Project",
        description="Test project description"
    )


@pytest.fixture
def tasks(db, tenant, project, user):
    """Create multiple test tasks"""
    task1 = Task.objects.create(
        tenant=tenant,
        project=project,
        title="Task 1",
        assignee=user,
        priority=Task.Priority.HIGH,
        status=Task.Status.TODO
    )
    task2 = Task.objects.create(
        tenant=tenant,
        project=project,
        title="Task 2",
        assignee=user,
        priority=Task.Priority.MEDIUM,
        status=Task.Status.IN_PROGRESS
    )
    task3 = Task.objects.create(
        tenant=tenant,
        project=project,
        title="Task 3",
        assignee=user,
        priority=Task.Priority.LOW,
        status=Task.Status.DONE
    )
    return [task1, task2, task3]


@pytest.mark.django_db
class TestLoginView:
    """Test login functionality"""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully"""
        response = client.get(reverse('login'))
        assert response.status_code == 200
        assert b'Sign in to your account' in response.content

    def test_successful_login(self, client, user):
        """Test successful login with valid credentials"""
        response = client.post(reverse('login'), {
            'email': 'user@example.com',
            'password': 'testpass123'
        })
        assert response.status_code == 302  # Redirect
        assert response.url == reverse('dashboard')

    def test_failed_login_invalid_credentials(self, client):
        """Test login fails with invalid credentials"""
        response = client.post(reverse('login'), {
            'email': 'wrong@example.com',
            'password': 'wrongpass'
        })
        assert response.status_code == 200
        assert b'Invalid email or password' in response.content

    def test_authenticated_user_redirects_from_login(self, client, user):
        """Test that authenticated users are redirected from login page"""
        client.force_login(user)
        response = client.get(reverse('login'))
        assert response.status_code == 302
        assert response.url == reverse('dashboard')


@pytest.mark.django_db
class TestDashboardView:
    """Test dashboard view"""

    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires authentication"""
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_dashboard_loads_for_authenticated_user(self, client, user):
        """Test dashboard loads for authenticated users"""
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200
        assert b'Dashboard' in response.content

    def test_dashboard_shows_task_statistics(self, client, user, tasks):
        """Test dashboard displays task statistics"""
        client.force_login(user)
        response = client.get(reverse('dashboard'))
        assert response.status_code == 200

        # Check statistics in context
        assert response.context['total_tasks'] == 3
        assert response.context['todo_count'] == 1
        assert response.context['in_progress_count'] == 1
        assert response.context['done_count'] == 1


@pytest.mark.django_db
class TestTaskListAPI:
    """Test task list API for DataTables"""

    def test_task_list_api_requires_login(self, client):
        """Test that task list API requires authentication"""
        response = client.get(reverse('api_tasks'))
        assert response.status_code == 302

    def test_task_list_api_returns_json(self, client, user, tasks):
        """Test that API returns JSON with tasks"""
        client.force_login(user)
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 25
        })
        assert response.status_code == 200

        data = json.loads(response.content)
        assert 'data' in data
        assert len(data['data']) == 3
        assert data['recordsTotal'] == 3
        assert data['recordsFiltered'] == 3

    def test_task_list_api_filters_by_status(self, client, user, tasks):
        """Test filtering tasks by status"""
        client.force_login(user)
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 25,
            'status': 'TODO'
        })

        data = json.loads(response.content)
        assert len(data['data']) == 1
        assert data['data'][0]['status_value'] == 'TODO'

    def test_task_list_api_filters_by_priority(self, client, user, tasks):
        """Test filtering tasks by priority"""
        client.force_login(user)
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 25,
            'priority': 'HIGH'
        })

        data = json.loads(response.content)
        assert len(data['data']) == 1
        assert data['data'][0]['priority_value'] == 'HIGH'

    def test_task_list_api_search(self, client, user, tasks):
        """Test searching tasks"""
        client.force_login(user)
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 25,
            'search[value]': 'Task 1'
        })

        data = json.loads(response.content)
        assert len(data['data']) == 1
        assert data['data'][0]['title'] == 'Task 1'

    def test_task_list_api_pagination(self, client, user, tasks):
        """Test pagination"""
        client.force_login(user)

        # Get first page with 2 items
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 2
        })

        data = json.loads(response.content)
        assert len(data['data']) == 2

        # Get second page
        response = client.get(reverse('api_tasks'), {
            'draw': 2,
            'start': 2,
            'length': 2
        })

        data = json.loads(response.content)
        assert len(data['data']) == 1


@pytest.mark.django_db
class TestTenantIsolationInUI:
    """Test that UI enforces tenant isolation"""

    def test_user_only_sees_own_tenant_tasks(self, client, user, other_user, tasks):
        """Test users only see tasks from their tenant"""
        # Create tasks for other tenant
        other_project = Project.objects.create(
            tenant=other_user.memberships.first().tenant,
            name="Other Project"
        )
        Task.objects.create(
            tenant=other_user.memberships.first().tenant,
            project=other_project,
            title="Other Tenant Task"
        )

        # Login as first user
        client.force_login(user)
        response = client.get(reverse('api_tasks'), {
            'draw': 1,
            'start': 0,
            'length': 25
        })

        data = json.loads(response.content)
        # Should only see 3 tasks from their own tenant
        assert len(data['data']) == 3
        assert all(task['title'] != 'Other Tenant Task' for task in data['data'])


@pytest.mark.django_db
class TestExportTasks:
    """Test CSV export functionality"""

    def test_export_requires_login(self, client):
        """Test that export requires authentication"""
        response = client.get(reverse('export_tasks'))
        assert response.status_code == 302

    def test_export_tasks_to_csv(self, client, user, tasks):
        """Test exporting tasks to CSV"""
        client.force_login(user)
        response = client.get(reverse('export_tasks'))

        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']
        assert 'tasks.csv' in response['Content-Disposition']

        # Check CSV content
        content = response.content.decode('utf-8')
        assert 'Title,Project,Assignee,Due Date,Priority,Status,Created At' in content
        assert 'Task 1' in content
        assert 'Task 2' in content
        assert 'Task 3' in content

    def test_export_respects_filters(self, client, user, tasks):
        """Test that export respects status filter"""
        client.force_login(user)
        response = client.get(reverse('export_tasks'), {'status': 'TODO'})

        content = response.content.decode('utf-8')
        assert 'Task 1' in content
        assert 'Task 2' not in content
        assert 'Task 3' not in content


@pytest.mark.django_db
class TestLogout:
    """Test logout functionality"""

    def test_logout_redirects_to_login(self, client, user):
        """Test that logout redirects to login page"""
        client.force_login(user)
        response = client.post(reverse('logout'))

        assert response.status_code == 302
        assert response.url == reverse('login')

        # Verify user is logged out
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302  # Redirected to login
