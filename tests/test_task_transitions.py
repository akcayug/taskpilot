import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from core.models import Tenant, TenantMembership
from tasks.models import Project, Task
from tasks.services import TaskService
from audit.models import AuditLog

User = get_user_model()


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
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MEMBER
    )
    return user


@pytest.fixture
def manager(db, tenant):
    """Create a manager user in the test tenant"""
    user = User.objects.create_user(
        email="manager@example.com",
        password="testpass123"
    )
    TenantMembership.objects.create(
        user=user,
        tenant=tenant,
        role=TenantMembership.Role.MANAGER
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
def task(db, tenant, project, user):
    """Create a test task"""
    return Task.objects.create(
        tenant=tenant,
        project=project,
        title="Test Task",
        description="Test task description",
        assignee=user,
        priority=Task.Priority.MEDIUM,
        status=Task.Status.TODO
    )


@pytest.mark.django_db
class TestProjectModel:
    """Test Project model"""

    def test_create_project(self, tenant):
        project = Project.objects.create(
            tenant=tenant,
            name="My Project",
            description="Project description"
        )
        assert project.name == "My Project"
        assert project.tenant == tenant

    def test_project_str(self, project, tenant):
        assert str(project) == f"{tenant.name} - Test Project"

    def test_unique_project_name_per_tenant(self, tenant, project):
        """Test that project names must be unique per tenant"""
        with pytest.raises(Exception):
            Project.objects.create(
                tenant=tenant,
                name="Test Project"  # Same name as fixture
            )

    def test_different_tenants_can_have_same_project_name(self, tenant, other_tenant):
        """Different tenants can have projects with the same name"""
        Project.objects.create(tenant=tenant, name="Shared Name")
        Project.objects.create(tenant=other_tenant, name="Shared Name")
        assert Project.objects.filter(name="Shared Name").count() == 2


@pytest.mark.django_db
class TestTaskModel:
    """Test Task model"""

    def test_create_task(self, task):
        assert task.title == "Test Task"
        assert task.status == Task.Status.TODO
        assert task.priority == Task.Priority.MEDIUM

    def test_task_str(self, task):
        assert str(task) == "Test Task (To Do)"

    def test_task_inherits_tenant_from_project(self, tenant, project):
        """Task should automatically inherit tenant from project"""
        task = Task.objects.create(
            project=project,
            title="Auto Tenant Task"
        )
        assert task.tenant == tenant
        assert task.tenant == project.tenant

    def test_task_priority_choices(self):
        """Test priority choices are correct"""
        assert Task.Priority.HIGH == 'HIGH'
        assert Task.Priority.MEDIUM == 'MEDIUM'
        assert Task.Priority.LOW == 'LOW'

    def test_task_status_choices(self):
        """Test status choices are correct"""
        assert Task.Status.TODO == 'TODO'
        assert Task.Status.IN_PROGRESS == 'IN_PROGRESS'
        assert Task.Status.DONE == 'DONE'
        assert Task.Status.ARCHIVED == 'ARCHIVED'


@pytest.mark.django_db
class TestTaskService:
    """Test TaskService business logic"""

    def test_create_task_with_service(self, tenant, project, user):
        """Test creating a task via service"""
        task = TaskService.create_task(
            tenant=tenant,
            project=project,
            title="Service Task",
            description="Created via service",
            assignee=user,
            priority=Task.Priority.HIGH,
            created_by=user
        )

        assert task.title == "Service Task"
        assert task.assignee == user
        assert task.priority == Task.Priority.HIGH

        # Verify audit log was created
        audit = AuditLog.objects.filter(
            resource_type='Task',
            resource_id=task.id,
            action='CREATE'
        ).first()
        assert audit is not None
        assert audit.changes['title'] == "Service Task"

    def test_cannot_assign_user_outside_tenant(self, tenant, project, other_user, manager):
        """Test that users outside the tenant cannot be assigned"""
        task = Task.objects.create(
            tenant=tenant,
            project=project,
            title="Test Task"
        )

        with pytest.raises(ValidationError) as exc_info:
            TaskService.assign_task(task, other_user, manager)

        assert "not a member of tenant" in str(exc_info.value)

    def test_valid_status_transitions(self, task, user):
        """Test all valid status transitions"""
        # TODO -> IN_PROGRESS
        TaskService.update_task_status(task, Task.Status.IN_PROGRESS, user)
        assert task.status == Task.Status.IN_PROGRESS

        # IN_PROGRESS -> DONE
        TaskService.update_task_status(task, Task.Status.DONE, user)
        assert task.status == Task.Status.DONE

        # DONE -> ARCHIVED
        TaskService.update_task_status(task, Task.Status.ARCHIVED, user)
        assert task.status == Task.Status.ARCHIVED

    def test_invalid_status_transition_todo_to_done(self, task, user):
        """Test that TODO cannot directly transition to DONE"""
        with pytest.raises(ValidationError) as exc_info:
            TaskService.update_task_status(task, Task.Status.DONE, user)

        assert "Cannot transition from TODO to DONE" in str(exc_info.value)

    def test_invalid_status_transition_from_archived(self, task, user):
        """Test that ARCHIVED state is final"""
        task.status = Task.Status.ARCHIVED
        task.save()

        with pytest.raises(ValidationError):
            TaskService.update_task_status(task, Task.Status.TODO, user)

    def test_status_transition_creates_audit_log(self, task, user):
        """Test that status transitions create audit logs"""
        TaskService.update_task_status(task, Task.Status.IN_PROGRESS, user)

        audit = AuditLog.objects.filter(
            resource_type='Task',
            resource_id=task.id,
            action='UPDATE_STATUS'
        ).first()

        assert audit is not None
        assert audit.user == user
        assert audit.changes['old_status'] == Task.Status.TODO
        assert audit.changes['new_status'] == Task.Status.IN_PROGRESS

    def test_assign_task_creates_audit_log(self, task, user, manager):
        """Test that task assignment creates audit log"""
        TaskService.assign_task(task, manager, user)

        audit = AuditLog.objects.filter(
            resource_type='Task',
            resource_id=task.id,
            action='ASSIGN'
        ).first()

        assert audit is not None
        assert audit.changes['old_assignee'] == user.email
        assert audit.changes['new_assignee'] == manager.email


@pytest.mark.django_db
class TestTenantIsolationForTasks:
    """Test that tasks are properly isolated by tenant"""

    def test_tasks_scoped_by_tenant(self, tenant, other_tenant, project):
        """Test that tasks are scoped by tenant"""
        other_project = Project.objects.create(
            tenant=other_tenant,
            name="Other Project"
        )

        # Create tasks in different tenants
        task1 = Task.objects.create(
            tenant=tenant,
            project=project,
            title="Tenant 1 Task"
        )
        task2 = Task.objects.create(
            tenant=other_tenant,
            project=other_project,
            title="Tenant 2 Task"
        )

        # Query by tenant
        tenant1_tasks = Task.objects.filter(tenant=tenant)
        tenant2_tasks = Task.objects.filter(tenant=other_tenant)

        assert task1 in tenant1_tasks
        assert task2 not in tenant1_tasks
        assert task2 in tenant2_tasks
        assert task1 not in tenant2_tasks

    def test_project_tasks_scoped_by_tenant(self, tenant, other_tenant, project):
        """Test that project's tasks are scoped by tenant"""
        # Create task in project
        Task.objects.create(
            tenant=tenant,
            project=project,
            title="Project Task"
        )

        # Project should only see its own tasks
        assert project.tasks.count() == 1
        assert project.tasks.first().tenant == tenant


@pytest.mark.django_db
class TestStatusTransitionRules:
    """Test specific status transition rules"""

    def test_all_valid_transitions_from_todo(self, task, user):
        """Test all valid transitions from TODO"""
        # TODO -> IN_PROGRESS
        task_copy = Task.objects.create(
            tenant=task.tenant,
            project=task.project,
            title="Test 1",
            status=Task.Status.TODO
        )
        TaskService.update_task_status(task_copy, Task.Status.IN_PROGRESS, user)
        assert task_copy.status == Task.Status.IN_PROGRESS

        # TODO -> ARCHIVED
        task_copy2 = Task.objects.create(
            tenant=task.tenant,
            project=task.project,
            title="Test 2",
            status=Task.Status.TODO
        )
        TaskService.update_task_status(task_copy2, Task.Status.ARCHIVED, user)
        assert task_copy2.status == Task.Status.ARCHIVED

    def test_all_valid_transitions_from_in_progress(self, task, user):
        """Test all valid transitions from IN_PROGRESS"""
        task.status = Task.Status.IN_PROGRESS
        task.save()

        # IN_PROGRESS -> DONE
        TaskService.update_task_status(task, Task.Status.DONE, user)
        assert task.status == Task.Status.DONE

        # Reset and test IN_PROGRESS -> TODO
        task.status = Task.Status.IN_PROGRESS
        task.save()
        TaskService.update_task_status(task, Task.Status.TODO, user)
        assert task.status == Task.Status.TODO

        # Reset and test IN_PROGRESS -> ARCHIVED
        task.status = Task.Status.IN_PROGRESS
        task.save()
        TaskService.update_task_status(task, Task.Status.ARCHIVED, user)
        assert task.status == Task.Status.ARCHIVED

    def test_all_valid_transitions_from_done(self, task, user):
        """Test all valid transitions from DONE"""
        task.status = Task.Status.DONE
        task.save()

        # DONE -> ARCHIVED
        TaskService.update_task_status(task, Task.Status.ARCHIVED, user)
        assert task.status == Task.Status.ARCHIVED

        # Reset and test DONE -> TODO
        task.status = Task.Status.DONE
        task.save()
        TaskService.update_task_status(task, Task.Status.TODO, user)
        assert task.status == Task.Status.TODO
