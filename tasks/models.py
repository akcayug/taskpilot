from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import Tenant


class Project(models.Model):
    """Project model scoped by tenant"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Financial fields (contract)
    contract_total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total contract amount"
    )
    contract_retention_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total retention amount withheld from contract"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
        unique_together = [['tenant', 'name']]

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"

    def get_latest_snapshot(self):
        """Get the most recent financial snapshot"""
        return self.snapshots.order_by('-created_at').first()

    def get_financial_kpis(self):
        """Calculate financial KPIs based on latest snapshot"""
        snapshot = self.get_latest_snapshot()

        if not snapshot:
            return {
                'completion_percentage': 0,
                'remaining_work': float(self.contract_total_amount),
                'paid_percentage': 0,
                'remaining_payment': float(self.contract_total_amount - self.contract_retention_total),
                'remaining_retention': float(self.contract_retention_total),
                'has_data': False
            }

        # Avoid division by zero
        completion_percentage = 0
        if self.contract_total_amount > 0:
            completion_percentage = (float(snapshot.total_completed_work) / float(self.contract_total_amount)) * 100

        remaining_work = float(self.contract_total_amount) - float(snapshot.total_completed_work)

        # Payment calculations (excluding retention)
        payment_base = float(self.contract_total_amount - self.contract_retention_total)
        paid_percentage = 0
        if payment_base > 0:
            paid_percentage = (float(snapshot.total_paid_amount) / payment_base) * 100

        remaining_payment = payment_base - float(snapshot.total_paid_amount)
        remaining_retention = float(self.contract_retention_total) - float(snapshot.total_retention_earned)

        return {
            'completion_percentage': round(completion_percentage, 2),
            'remaining_work': round(remaining_work, 2),
            'paid_percentage': round(paid_percentage, 2),
            'remaining_payment': round(remaining_payment, 2),
            'remaining_retention': round(remaining_retention, 2),
            'has_data': True
        }


class Task(models.Model):
    """Task model with status transitions and tenant isolation"""

    class Priority(models.TextChoices):
        HIGH = 'HIGH', _('High')
        MEDIUM = 'MEDIUM', _('Medium')
        LOW = 'LOW', _('Low')

    class Status(models.TextChoices):
        TODO = 'TODO', _('To Do')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        DONE = 'DONE', _('Done')
        ARCHIVED = 'ARCHIVED', _('Archived')

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tasks')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'assignee']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Ensure task's tenant matches project's tenant
        if self.project:
            self.tenant = self.project.tenant
        super().save(*args, **kwargs)


class ProjectFinancialSnapshot(models.Model):
    """Financial snapshot for project tracking"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='snapshots')

    # User input values
    total_completed_work = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total value of completed work"
    )
    total_paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total amount paid (excluding retention)"
    )
    total_retention_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total retention earned/released"
    )

    notes = models.TextField(blank=True, help_text="Optional notes about this snapshot")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='financial_snapshots'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_financial_snapshots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
        ]

    def __str__(self):
        return f"{self.project.name} - Snapshot {self.created_at.strftime('%Y-%m-%d')}"
