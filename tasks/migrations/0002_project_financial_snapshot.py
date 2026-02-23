# Generated manually for TASK-06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="contract_total_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Total contract amount",
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="contract_retention_total",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Total retention amount withheld from contract",
                max_digits=12,
            ),
        ),
        migrations.CreateModel(
            name="ProjectFinancialSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "total_completed_work",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total value of completed work",
                        max_digits=12,
                    ),
                ),
                (
                    "total_paid_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total amount paid (excluding retention)",
                        max_digits=12,
                    ),
                ),
                (
                    "total_retention_earned",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total retention earned/released",
                        max_digits=12,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Optional notes about this snapshot",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="financial_snapshots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="tasks.project",
                    ),
                ),
            ],
            options={
                "db_table": "project_financial_snapshots",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["project", "-created_at"],
                        name="project_fin_project_idx",
                    ),
                ],
            },
        ),
    ]
