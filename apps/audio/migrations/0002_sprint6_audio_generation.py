# Generated manually for Sprint 6 audio generation

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audio", "0001_initial"),
        ("scripts", "0002_sprint5_script_generation"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoiceProfile",
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
                ("name", models.CharField(max_length=100, unique=True)),
                ("provider", models.CharField(db_index=True, max_length=100)),
                (
                    "provider_voice_id",
                    models.CharField(
                        help_text="Provider-specific voice identifier (never exposed to business callers).",
                        max_length=255,
                    ),
                ),
                (
                    "language",
                    models.CharField(db_index=True, default="en", max_length=10),
                ),
                ("gender", models.CharField(blank=True, max_length=20)),
                ("description", models.TextField(blank=True)),
                ("default_speed", models.FloatField(default=1.0)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "ordering": ["provider", "name"],
            },
        ),
        migrations.CreateModel(
            name="PersonaVoiceMapping",
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
                (
                    "persona",
                    models.CharField(
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
                ("provider", models.CharField(db_index=True, max_length=100)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                (
                    "voice_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="persona_mappings",
                        to="audio.voiceprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["provider", "persona"],
            },
        ),
        migrations.AddField(
            model_name="audioasset",
            name="bitrate",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="audioasset",
            name="format",
            field=models.CharField(blank=True, db_index=True, max_length=20),
        ),
        migrations.AddField(
            model_name="audioasset",
            name="generated_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="audioasset",
            name="generation_time",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="audioasset",
            name="sample_rate",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="audioasset",
            name="voice",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddIndex(
            model_name="voiceprofile",
            index=models.Index(
                fields=["provider", "enabled"],
                name="audio_voice_provider_enabled_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="voiceprofile",
            index=models.Index(
                fields=["provider", "language"],
                name="audio_voice_provider_language_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="personavoicemapping",
            constraint=models.UniqueConstraint(
                fields=("persona", "provider"),
                name="unique_persona_provider_voice_mapping",
            ),
        ),
    ]
