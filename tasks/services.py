from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Task
from core.models import TenantMembership


class TaskService:
    """Business logic service for task operations with status transitions and audit logging"""

    # Valid status transitions
    VALID_TRANSITIONS = {
        Task.Status.TODO: [Task.Status.IN_PROGRESS, Task.Status.ARCHIVED],
        Task.Status.IN_PROGRESS: [Task.Status.DONE, Task.Status.TODO, Task.Status.ARCHIVED],
        Task.Status.DONE: [Task.Status.ARCHIVED, Task.Status.TODO],
        Task.Status.ARCHIVED: [],  # Cannot transition from archived
    }

    @classmethod
    def validate_status_transition(cls, task, new_status):
        """
        Validate if status transition is allowed.
        Raises ValidationError if transition is invalid.
        """
        current_status = task.status
        valid_next_statuses = cls.VALID_TRANSITIONS.get(current_status, [])

        if new_status not in valid_next_statuses:
            raise ValidationError(
                f"Cannot transition from {current_status} to {new_status}. "
                f"Valid transitions: {', '.join(valid_next_statuses)}"
            )

    @classmethod
    def validate_assignee_in_tenant(cls, task, assignee):
        """
        Validate that assignee belongs to the task's tenant.
        Raises ValidationError if assignee is not in tenant.
        """
        if assignee is None:
            return  # Unassigning is allowed

        membership = TenantMembership.objects.filter(
            user=assignee,
            tenant=task.tenant
        ).first()

        if not membership:
            raise ValidationError(
                f"User {assignee.email} is not a member of tenant {task.tenant.name}"
            )

    @classmethod
    @transaction.atomic
    def create_task(cls, tenant, project, title, **kwargs):
        """
        Create a new task with validation.
        """
        # Extract created_by for audit log
        created_by = kwargs.pop('created_by', None)
        assignee = kwargs.get('assignee')

        # Create task
        task = Task(
            tenant=tenant,
            project=project,
            title=title,
            **kwargs
        )

        # Validate assignee if provided
        if assignee:
            cls.validate_assignee_in_tenant(task, assignee)

        task.save()

        # Create audit log
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='CREATE',
            resource_type='Task',
            resource_id=task.id,
            changes={'status': task.status, 'title': title}
        )

        return task

    @classmethod
    @transaction.atomic
    def update_task_status(cls, task, new_status, user):
        """
        Update task status with validation and audit logging.
        """
        old_status = task.status

        # Skip if status hasn't changed
        if old_status == new_status:
            return task

        # Validate transition
        cls.validate_status_transition(task, new_status)

        # Update status
        task.status = new_status
        task.save()

        # Create audit log
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action='UPDATE_STATUS',
            resource_type='Task',
            resource_id=task.id,
            changes={
                'old_status': old_status,
                'new_status': new_status
            }
        )

        return task

    @classmethod
    @transaction.atomic
    def assign_task(cls, task, assignee, user):
        """
        Assign task to a user with validation and audit logging.
        """
        old_assignee = task.assignee

        # Validate assignee is in tenant
        cls.validate_assignee_in_tenant(task, assignee)

        # Update assignee
        task.assignee = assignee
        task.save()

        # Create audit log
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action='ASSIGN',
            resource_type='Task',
            resource_id=task.id,
            changes={
                'old_assignee': old_assignee.email if old_assignee else None,
                'new_assignee': assignee.email if assignee else None
            }
        )

        return task
