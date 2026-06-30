"""News source serializers."""

from rest_framework import serializers

from apps.providers.models import NewsSource, ProviderHealthCheck


class NewsSourceListSerializer(serializers.ModelSerializer):
    """Compact news source list representation."""

    class Meta:
        model = NewsSource
        fields = (
            "id",
            "name",
            "provider_type",
            "language",
            "enabled",
            "max_articles_per_import",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class NewsSourceDetailSerializer(serializers.ModelSerializer):
    """Full news source representation."""

    class Meta:
        model = NewsSource
        fields = (
            "id",
            "name",
            "provider_type",
            "homepage",
            "rss_url",
            "language",
            "enabled",
            "max_articles_per_import",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class NewsSourceWriteSerializer(serializers.ModelSerializer):
    """News source create and update payload."""

    class Meta:
        model = NewsSource
        fields = (
            "name",
            "provider_type",
            "homepage",
            "rss_url",
            "language",
            "enabled",
            "max_articles_per_import",
        )


class ProviderHealthCheckSerializer(serializers.ModelSerializer):
    """Provider health check record."""

    class Meta:
        model = ProviderHealthCheck
        fields = (
            "id",
            "news_source",
            "provider_type",
            "provider_name",
            "status",
            "response_time_ms",
            "details",
            "checked_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
