"""Article and tagging models."""

from django.db import models

from apps.core.models import DomainModel, UUIDModel


class ArticleStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COLLECTED = "collected", "Collected"
    PROCESSED = "processed", "Processed"
    SELECTED = "selected", "Selected"
    USED = "used", "Used"
    ARCHIVED = "archived", "Archived"
    FAILED = "failed", "Failed"


class Article(DomainModel):
    """Represents a collected news article."""

    source = models.ForeignKey(
        "providers.NewsSource",
        on_delete=models.PROTECT,
        related_name="articles",
    )
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=1000, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    language = models.CharField(max_length=10, default="en", db_index=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.PENDING,
        db_index=True,
    )
    tags = models.ManyToManyField(
        "articles.Tag",
        through="articles.ArticleTag",
        related_name="articles",
        blank=True,
    )

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["source", "status"]),
        ]

    def __str__(self) -> str:
        return self.title


class Tag(UUIDModel):
    """Reusable label for categorizing articles."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ArticleTag(models.Model):
    """Many-to-many relation between articles and tags."""

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="article_tags",
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name="article_tags",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "tag"],
                name="unique_article_tag",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.article.title} — {self.tag.name}"
