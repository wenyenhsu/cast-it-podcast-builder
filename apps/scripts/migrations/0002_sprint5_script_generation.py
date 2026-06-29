# Generated manually for Sprint 5 script generation

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scripts", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scriptsegment",
            old_name="duration_seconds",
            new_name="estimated_duration_seconds",
        ),
        migrations.AddField(
            model_name="script",
            name="estimated_duration_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="script",
            name="generated_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="script",
            name="model_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="script",
            name="title",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="script",
            name="validation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("passed", "Passed"),
                    ("failed", "Failed"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="scriptsegment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="scriptsegment",
            name="pause_after_seconds",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="scriptsegment",
            name="pause_before_seconds",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="scriptsegment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name="script",
            name="prompt_version",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="scriptsegment",
            name="speaker",
            field=models.CharField(
                choices=[
                    ("expert", "Expert"),
                    ("beginner", "Beginner"),
                    ("narration", "Narration"),
                    ("intro", "Intro"),
                    ("outro", "Outro"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="ScriptMetadata",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=False)),
                ("source_article_ids", models.JSONField(blank=True, default=list)),
                ("selected_topics", models.JSONField(blank=True, default=list)),
                ("generation_notes", models.TextField(blank=True)),
                ("token_usage", models.JSONField(blank=True, default=dict)),
                ("validation_results", models.JSONField(blank=True, default=dict)),
                (
                    "script",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metadata",
                        to="scripts.script",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "script metadata",
            },
        ),
        migrations.AddIndex(
            model_name="script",
            index=models.Index(
                fields=["episode", "validation_status"],
                name="scripts_scr_episode_val_idx",
            ),
        ),
    ]
