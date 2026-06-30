"""Initial observability models."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="OperationalEvent",
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
                ("event_type", models.CharField(db_index=True, max_length=100)),
                ("severity", models.CharField(db_index=True, max_length=20)),
                ("source", models.CharField(max_length=100)),
                ("name", models.CharField(db_index=True, max_length=200)),
                ("message", models.TextField()),
                (
                    "correlation_id",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                (
                    "request_id",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                ("job_id", models.CharField(blank=True, db_index=True, max_length=64)),
                (
                    "workflow_run_id",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                (
                    "episode_id",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                (
                    "provider",
                    models.CharField(blank=True, db_index=True, max_length=100),
                ),
                ("duration_ms", models.FloatField(blank=True, null=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["event_type", "created_at"],
                        name="observabili_event_t_0f8b0d_idx",
                    ),
                    models.Index(
                        fields=["severity", "created_at"],
                        name="observabili_severit_6d8f2a_idx",
                    ),
                ],
            },
        ),
    ]
