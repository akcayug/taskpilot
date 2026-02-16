from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Audit log for tracking all changes to resources"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50)  # CREATE, UPDATE, DELETE, UPDATE_STATUS, ASSIGN, etc.
    resource_type = models.CharField(max_length=50)  # Task, Project, etc.
    resource_id = models.IntegerField()
    changes = models.JSONField()  # Store the actual changes
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else 'System'
        return f"{user_email} - {self.action} {self.resource_type}#{self.resource_id}"
