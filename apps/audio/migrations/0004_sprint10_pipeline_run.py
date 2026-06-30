"""Sprint 10 pipeline run tracking model."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("episodes", "0001_initial"),
        ("audio", "0003_sprint7_audio_pipeline"),
    ]

    operations = [
        migrations.CreateModel(
            name="PipelineRun",
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
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("output_path", models.CharField(blank=True, max_length=500)),
                ("error_message", models.TextField(blank=True)),
                (
                    "audio_asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="pipeline_runs",
                        to="audio.audioasset",
                    ),
                ),
                (
                    "episode",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="pipeline_runs",
                        to="episodes.episode",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="pipelinerun",
            index=models.Index(
                fields=["episode", "status"],
                name="audio_pipe_episode_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="pipelinerun",
            index=models.Index(
                fields=["status", "created_at"],
                name="audio_pipe_status_created_idx",
            ),
        ),
    ]
