"""Article and tag serializers."""

from rest_framework import serializers

from api.v1.exceptions import ConflictError
from apps.articles.models import Article, Tag
from services.news.content_hash import ContentHashService


class TagSerializer(serializers.ModelSerializer):
    """Tag representation."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id",)


class ArticleListSerializer(serializers.ModelSerializer):
    """Compact article list representation."""

    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "source",
            "source_name",
            "title",
            "url",
            "published_at",
            "language",
            "category",
            "importance_score",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Full article representation."""

    source_name = serializers.CharField(source="source.name", read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Article
        fields = (
            "id",
            "source",
            "source_name",
            "title",
            "author",
            "url",
            "published_at",
            "language",
            "category",
            "summary",
            "content",
            "content_hash",
            "importance_score",
            "summary_generated_at",
            "classified_at",
            "keywords_generated_at",
            "status",
            "tag_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "content_hash",
            "summary_generated_at",
            "classified_at",
            "keywords_generated_at",
            "created_at",
            "updated_at",
        )


class ArticleWriteSerializer(serializers.ModelSerializer):
    """Article create and update payload."""

    class Meta:
        model = Article
        fields = (
            "source",
            "title",
            "author",
            "url",
            "published_at",
            "language",
            "category",
            "summary",
            "content",
            "importance_score",
            "status",
        )

    def create(self, validated_data: dict) -> Article:
        hash_service = ContentHashService()
        content = validated_data.get("content", "")
        title = validated_data.get("title", "")
        content_hash = hash_service.generate_hash(content, fallback_title=title)
        if Article.objects.filter(content_hash=content_hash).exists():
            raise ConflictError(
                detail="An article with the same content already exists."
            )
        validated_data["content_hash"] = content_hash
        return super().create(validated_data)

    def update(self, instance: Article, validated_data: dict) -> Article:
        content = validated_data.get("content", instance.content)
        title = validated_data.get("title", instance.title)
        content_hash = ContentHashService().generate_hash(
            content,
            fallback_title=title,
        )
        duplicate = Article.objects.filter(content_hash=content_hash).exclude(
            pk=instance.pk
        )
        if duplicate.exists():
            raise ConflictError(
                detail="An article with the same content already exists."
            )
        validated_data["content_hash"] = content_hash
        return super().update(instance, validated_data)


class ArticleImportSerializer(serializers.Serializer):
    """Optional payload for bulk article import."""

    source_id = serializers.UUIDField(required=False, allow_null=True)
