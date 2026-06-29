# Generated manually for Sprint 9 publishing layer.

import uuid

import django.utils.timezone
from django.db import migrations, models


def backfill_publish_job_timestamps(apps, schema_editor):
    PublishJob = apps.get_model("publish", "PublishJob")
    now = django.utils.timezone.now()
    PublishJob.objects.filter(created_at__isnull=True).update(
        created_at=now,
        updated_at=now,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("episodes", "0001_initial"),
        ("publish", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="publishjob",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="publishjob",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="publishjob",
            name="external_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="publishjob",
            name="platform",
            field=models.CharField(
                choices=[
                    ("youtube", "YouTube"),
                    ("rss", "RSS"),
                    ("spotify", "Spotify"),
                    ("apple_podcasts", "Apple Podcasts"),
                    ("twitch", "Twitch"),
                    ("webapp", "Web App"),
                    ("mobile_app", "Mobile App"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="publishjob",
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PublishedEpisode",
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
                    "platform",
                    models.CharField(
                        choices=[
                            ("youtube", "YouTube"),
                            ("rss", "RSS"),
                            ("spotify", "Spotify"),
                            ("apple_podcasts", "Apple Podcasts"),
                            ("twitch", "Twitch"),
                            ("webapp", "Web App"),
                            ("mobile_app", "Mobile App"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("published_url", models.URLField(max_length=1000)),
                (
                    "external_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("published_at", models.DateTimeField(db_index=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "episode",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="published_episodes",
                        to="episodes.episode",
                    ),
                ),
            ],
            options={
                "ordering": ["-published_at"],
            },
        ),
        migrations.AddIndex(
            model_name="publishedepisode",
            index=models.Index(
                fields=["episode", "platform"],
                name="publish_pub_episode_platform_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="publishedepisode",
            index=models.Index(
                fields=["platform", "published_at"],
                name="publish_pub_platform_published_idx",
            ),
        ),
        migrations.RunPython(
            backfill_publish_job_timestamps,
            migrations.RunPython.noop,
        ),
    ]
