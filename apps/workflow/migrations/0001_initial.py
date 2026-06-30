# Generated manually for Sprint 13 workflow engine

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("episodes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowDefinition",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(db_index=True, max_length=100)),
                ("version", models.PositiveIntegerField(default=1)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "ordering": ["name", "-version"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("paused", "Paused"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                            ("retrying", "Retrying"),
                            ("skipped", "Skipped"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("current_step", models.CharField(blank=True, max_length=100)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                (
                    "episode",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="workflow_runs",
                        to="episodes.episode",
                    ),
                ),
                (
                    "workflow_definition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="runs",
                        to="workflow.workflowdefinition",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowStep",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("sequence", models.PositiveIntegerField()),
                (
                    "step_type",
                    models.CharField(
                        choices=[
                            ("index_knowledge", "Index Knowledge"),
                            ("collect_articles", "Collect Articles"),
                            ("summarize_articles", "Summarize Articles"),
                            ("classify_articles", "Classify Articles"),
                            ("rank_articles", "Rank Articles"),
                            ("plan_episode", "Plan Episode"),
                            ("generate_script", "Generate Script"),
                            ("generate_audio", "Generate Audio"),
                            ("process_audio", "Process Audio"),
                            ("publish_episode", "Publish Episode"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ("timeout_seconds", models.PositiveIntegerField(default=3600)),
                ("retry_limit", models.PositiveSmallIntegerField(default=3)),
                ("config", models.JSONField(blank=True, default=dict)),
                (
                    "workflow_definition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="workflow.workflowdefinition",
                    ),
                ),
            ],
            options={
                "ordering": ["workflow_definition", "sequence"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowStepRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("paused", "Paused"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                            ("retrying", "Retrying"),
                            ("skipped", "Skipped"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("input_data", models.JSONField(blank=True, default=dict)),
                ("output_data", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                (
                    "workflow_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="step_runs",
                        to="workflow.workflowrun",
                    ),
                ),
                (
                    "workflow_step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="step_runs",
                        to="workflow.workflowstep",
                    ),
                ),
            ],
            options={
                "ordering": ["workflow_run", "workflow_step__sequence"],
            },
        ),
        migrations.AddConstraint(
            model_name="workflowdefinition",
            constraint=models.UniqueConstraint(
                fields=("name", "version"),
                name="unique_workflow_definition_version",
            ),
        ),
        migrations.AddIndex(
            model_name="workflowrun",
            index=models.Index(
                fields=["status", "created_at"],
                name="workflow_w_status_0a1b2c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workflowrun",
            index=models.Index(
                fields=["workflow_definition", "status"],
                name="workflow_w_workflo_1b2c3d_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowrun",
            constraint=models.CheckConstraint(
                condition=models.Q(("progress__gte", 0), ("progress__lte", 100)),
                name="workflow_run_progress_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowstep",
            constraint=models.UniqueConstraint(
                fields=("workflow_definition", "sequence"),
                name="unique_workflow_step_sequence",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowstep",
            constraint=models.UniqueConstraint(
                fields=("workflow_definition", "name"),
                name="unique_workflow_step_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowsteprun",
            constraint=models.UniqueConstraint(
                fields=("workflow_run", "workflow_step"),
                name="unique_workflow_step_run",
            ),
        ),
        migrations.AddConstraint(
            model_name="workflowsteprun",
            constraint=models.CheckConstraint(
                condition=models.Q(("progress__gte", 0), ("progress__lte", 100)),
                name="workflow_step_run_progress_range",
            ),
        ),
    ]
