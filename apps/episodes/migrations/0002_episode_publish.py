"""Add the publish gate flag.

Episodes that already have final ready audio were live before the gate
existed (and are already on the Supabase shelf), so they are backfilled
to 1; everything else stays hidden until explicitly flipped.
"""

from django.db import migrations, models


def backfill_published(apps, schema_editor):
    Episode = apps.get_model("episodes", "Episode")
    AudioAsset = apps.get_model("audio", "AudioAsset")
    live_ids = (
        AudioAsset.objects.filter(
            is_final_episode_audio=True,
            status="ready",
        )
        .exclude(file_path="")
        .values_list("episode_id", flat=True)
        .distinct()
    )
    Episode.objects.filter(id__in=live_ids).update(publish=1)


class Migration(migrations.Migration):
    dependencies = [
        ("audio", "0005_audioasset_article"),
        ("episodes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="episode",
            name="publish",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Hidden"), (1, "Published")],
                db_index=True,
                default=0,
                help_text=(
                    "Listener gate: only episodes set to 1 are publicly visible."
                ),
            ),
        ),
        migrations.RunPython(backfill_published, migrations.RunPython.noop),
    ]
