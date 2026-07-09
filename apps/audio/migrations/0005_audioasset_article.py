import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0003_article_selected_for_script"),
        ("audio", "0004_sprint10_pipeline_run"),
    ]

    operations = [
        migrations.AddField(
            model_name="audioasset",
            name="article",
            field=models.ForeignKey(
                blank=True,
                help_text="Set on per-chapter audio: the article this chapter covers.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="chapter_audio_assets",
                to="articles.article",
            ),
        ),
    ]
