"""
Signal handlers for audit logging.
Automatically logs changes to critical models.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from audit.models import AuditLog


@receiver(post_save, sender='tasks.Task')
def log_task_save(sender, instance, created, **kwargs):
    """Log task creation and updates."""
    action = 'CREATE' if created else 'UPDATE'

    # Get the user who made the change (stored in instance if available)
    user = getattr(instance, '_changed_by', None)

    changes = {
        'title': instance.title,
        'status': instance.status,
        'priority': instance.priority,
        'assignee_id': instance.assignee_id,
        'due_date': str(instance.due_date) if instance.due_date else None,
    }

    # For updates, try to get old values
    if not created:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            changes['old_status'] = old_instance.status
            changes['old_priority'] = old_instance.priority
            changes['old_assignee_id'] = old_instance.assignee_id
        except sender.DoesNotExist:
            pass

    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type='Task',
        resource_id=instance.id,
        changes=changes
    )


@receiver(post_delete, sender='tasks.Task')
def log_task_delete(sender, instance, **kwargs):
    """Log task deletion."""
    user = getattr(instance, '_deleted_by', None)

    AuditLog.objects.create(
        user=user,
        action='DELETE',
        resource_type='Task',
        resource_id=instance.id,
        changes={
            'title': instance.title,
            'status': instance.status,
        }
    )


@receiver(post_save, sender='tasks.Project')
def log_project_save(sender, instance, created, **kwargs):
    """Log project creation and updates."""
    action = 'CREATE' if created else 'UPDATE'
    user = getattr(instance, '_changed_by', None)

    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type='Project',
        resource_id=instance.id,
        changes={
            'name': instance.name,
            'description': instance.description,
        }
    )


@receiver(post_save, sender='users.Invitation')
def log_invitation_save(sender, instance, created, **kwargs):
    """Log invitation creation and acceptance."""
    if created:
        AuditLog.objects.create(
            user=instance.invited_by,
            action='INVITE_CREATED',
            resource_type='Invitation',
            resource_id=instance.id,
            changes={
                'email': instance.email,
                'role': instance.role,
            }
        )
    elif instance.accepted:
        AuditLog.objects.create(
            user=instance.invited_by,
            action='INVITE_ACCEPTED',
            resource_type='Invitation',
            resource_id=instance.id,
            changes={
                'email': instance.email,
                'accepted_at': str(instance.accepted_at) if hasattr(instance, 'accepted_at') else None,
            }
        )
