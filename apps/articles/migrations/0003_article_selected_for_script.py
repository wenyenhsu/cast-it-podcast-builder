"""Add script source selection flag to articles."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0002_article_intelligence_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="selected_for_script",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Include this article as source material for script generation.",
            ),
        ),
    ]
