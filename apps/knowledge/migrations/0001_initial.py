# Generated manually for Sprint 12 RAG knowledge base

import uuid

import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        pgvector.django.VectorExtension(),
        migrations.CreateModel(
            name="KnowledgeDocument",
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
                    "source_type",
                    models.CharField(
                        choices=[
                            ("article", "Article"),
                            ("episode", "Podcast Episode"),
                            ("script", "Podcast Script"),
                            ("newsletter", "Newsletter"),
                            ("documentation", "Documentation"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("source_id", models.CharField(db_index=True, max_length=64)),
                ("title", models.CharField(max_length=500)),
                (
                    "language",
                    models.CharField(db_index=True, default="en", max_length=10),
                ),
                ("content", models.TextField()),
                ("checksum", models.CharField(db_index=True, max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
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
                ("sequence", models.PositiveIntegerField()),
                ("text", models.TextField()),
                ("token_count", models.PositiveIntegerField(default=0)),
                (
                    "embedding_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "embedding",
                    pgvector.django.VectorField(blank=True, dimensions=768, null=True),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="chunks",
                        to="knowledge.knowledgedocument",
                    ),
                ),
            ],
            options={
                "ordering": ["document", "sequence"],
            },
        ),
        migrations.AddIndex(
            model_name="knowledgedocument",
            index=models.Index(
                fields=["source_type", "language"],
                name="knowledge_k_source__8a0f0d_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgedocument",
            index=models.Index(fields=["checksum"], name="knowledge_k_checksu_0d0b0a_idx"),
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.UniqueConstraint(
                fields=("source_type", "source_id"),
                name="unique_knowledge_document_source",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(
                fields=["document", "embedding_status"],
                name="knowledge_k_documen_6d0b0b_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgechunk",
            constraint=models.UniqueConstraint(
                fields=("document", "sequence"),
                name="unique_knowledge_chunk_sequence",
            ),
        ),
    ]
