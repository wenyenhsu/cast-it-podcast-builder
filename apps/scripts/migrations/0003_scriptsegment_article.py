import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0003_article_selected_for_script"),
        ("scripts", "0002_sprint5_script_generation"),
    ]

    operations = [
        migrations.AddField(
            model_name="scriptsegment",
            name="article",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Source article this segment discusses (chaptered generation)."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="script_segments",
                to="articles.article",
            ),
        ),
    ]
