# Generated manually for Sprint 7 audio pipeline

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audio", "0002_sprint6_audio_generation"),
    ]

    operations = [
        migrations.AddField(
            model_name="audioasset",
            name="is_final_episode_audio",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name="audioasset",
            index=models.Index(
                fields=["episode", "is_final_episode_audio"],
                name="audio_asset_episode_final_idx",
            ),
        ),
    ]
