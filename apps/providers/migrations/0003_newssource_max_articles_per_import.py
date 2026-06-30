"""Add per-import article limit to news sources."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("providers", "0002_sprint10_provider_health_check"),
    ]

    operations = [
        migrations.AddField(
            model_name="newssource",
            name="max_articles_per_import",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Maximum articles to import per run (0 = no limit).",
            ),
        ),
    ]
