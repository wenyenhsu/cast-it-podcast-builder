# Generated manually for Sprint 8 job system

from django.db import migrations, models


def migrate_completed_to_succeeded(apps, schema_editor) -> None:
    Job = apps.get_model("scheduler", "Job")
    Job.objects.filter(status="completed").update(status="succeeded")


class Migration(migrations.Migration):

    dependencies = [
        ("scheduler", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="job",
            old_name="error",
            new_name="error_message",
        ),
        migrations.AddField(
            model_name="job",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="retry_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="job",
            name="celery_task_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="job",
            name="job_type",
            field=models.CharField(
                choices=[
                    ("import_news", "Import News"),
                    ("summarize_article", "Summarize Article"),
                    ("classify_article", "Classify Article"),
                    ("episode_planning", "Episode Planning"),
                    ("generate_script", "Generate Script"),
                    ("generate_audio", "Generate Audio"),
                    ("run_audio_pipeline", "Run Audio Pipeline"),
                    ("publish_episode", "Publish Episode"),
                    ("retry_job", "Retry Job"),
                    ("health_check", "Health Check"),
                    ("custom", "Custom"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                    ("retrying", "Retrying"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            migrate_completed_to_succeeded,
            migrations.RunPython.noop,
        ),
        migrations.AlterModelOptions(
            name="job",
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(
                fields=["status", "created_at"],
                name="scheduler_job_status_created_idx",
            ),
        ),
    ]
