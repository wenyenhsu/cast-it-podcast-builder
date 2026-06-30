"""Sprint 10 provider health check model."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("providers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderHealthCheck",
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
                ("provider_type", models.CharField(db_index=True, max_length=50)),
                ("provider_name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("healthy", "Healthy"),
                            ("unhealthy", "Unhealthy"),
                            ("unknown", "Unknown"),
                        ],
                        db_index=True,
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("response_time_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("checked_at", models.DateTimeField(db_index=True)),
                (
                    "news_source",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        related_name="health_checks",
                        to="providers.newssource",
                    ),
                ),
            ],
            options={
                "ordering": ["-checked_at"],
            },
        ),
        migrations.AddIndex(
            model_name="providerhealthcheck",
            index=models.Index(
                fields=["provider_type", "status"],
                name="providers_pr_provider_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="providerhealthcheck",
            index=models.Index(
                fields=["news_source", "checked_at"],
                name="providers_pr_source_checked_idx",
            ),
        ),
    ]
