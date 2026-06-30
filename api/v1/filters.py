"""API filter sets."""

import django_filters

from apps.articles.models import Article, Tag
from apps.audio.models import AudioAsset, PersonaVoiceMapping, PipelineRun, VoiceProfile
from apps.episodes.models import Episode
from apps.providers.models import NewsSource, ProviderHealthCheck
from apps.publish.models import PublishJob
from apps.scheduler.models import Job
from apps.scripts.models import Script, ScriptSegment


class ArticleFilter(django_filters.FilterSet):
    """Filters for article list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    source = django_filters.UUIDFilter(field_name="source_id")
    language = django_filters.CharFilter(field_name="language")
    category = django_filters.CharFilter(field_name="category")
    published_after = django_filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="gte",
    )
    published_before = django_filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="lte",
    )
    min_score = django_filters.NumberFilter(
        field_name="importance_score",
        lookup_expr="gte",
    )

    class Meta:
        model = Article
        fields = (
            "status",
            "source",
            "language",
            "category",
            "published_after",
            "published_before",
            "min_score",
        )


class TagFilter(django_filters.FilterSet):
    """Filters for tag list endpoints."""

    class Meta:
        model = Tag
        fields = ("slug",)


class NewsSourceFilter(django_filters.FilterSet):
    """Filters for news source list endpoints."""

    provider_type = django_filters.CharFilter(field_name="provider_type")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    language = django_filters.CharFilter(field_name="language")

    class Meta:
        model = NewsSource
        fields = ("provider_type", "enabled", "language")


class EpisodeFilter(django_filters.FilterSet):
    """Filters for episode list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    language = django_filters.CharFilter(field_name="language")
    publish_date_after = django_filters.DateFilter(
        field_name="publish_date",
        lookup_expr="gte",
    )
    publish_date_before = django_filters.DateFilter(
        field_name="publish_date",
        lookup_expr="lte",
    )

    class Meta:
        model = Episode
        fields = ("status", "language", "publish_date_after", "publish_date_before")


class ScriptFilter(django_filters.FilterSet):
    """Filters for script list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    validation_status = django_filters.CharFilter(field_name="validation_status")
    episode = django_filters.UUIDFilter(field_name="episode_id")

    class Meta:
        model = Script
        fields = ("status", "validation_status", "episode")


class ScriptSegmentFilter(django_filters.FilterSet):
    """Filters for script segment list endpoints."""

    script = django_filters.UUIDFilter(field_name="script_id")
    speaker = django_filters.CharFilter(field_name="speaker")

    class Meta:
        model = ScriptSegment
        fields = ("script", "speaker")


class AudioAssetFilter(django_filters.FilterSet):
    """Filters for audio asset list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    episode = django_filters.UUIDFilter(field_name="episode_id")
    is_final_episode_audio = django_filters.BooleanFilter(
        field_name="is_final_episode_audio",
    )

    class Meta:
        model = AudioAsset
        fields = ("status", "episode", "is_final_episode_audio")


class PublishJobFilter(django_filters.FilterSet):
    """Filters for publish job list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    platform = django_filters.CharFilter(field_name="platform")
    episode = django_filters.UUIDFilter(field_name="episode_id")

    class Meta:
        model = PublishJob
        fields = ("status", "platform", "episode")


class JobFilter(django_filters.FilterSet):
    """Filters for background job list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    job_type = django_filters.CharFilter(field_name="job_type")

    class Meta:
        model = Job
        fields = ("status", "job_type")


class VoiceProfileFilter(django_filters.FilterSet):
    """Filters for voice profile list endpoints."""

    provider = django_filters.CharFilter(field_name="provider")
    enabled = django_filters.BooleanFilter(field_name="enabled")
    language = django_filters.CharFilter(field_name="language")

    class Meta:
        model = VoiceProfile
        fields = ("provider", "enabled", "language")


class PersonaVoiceMappingFilter(django_filters.FilterSet):
    """Filters for persona voice mapping list endpoints."""

    persona = django_filters.CharFilter(field_name="persona")
    provider = django_filters.CharFilter(field_name="provider")
    enabled = django_filters.BooleanFilter(field_name="enabled")

    class Meta:
        model = PersonaVoiceMapping
        fields = ("persona", "provider", "enabled")


class ProviderHealthCheckFilter(django_filters.FilterSet):
    """Filters for provider health check list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    provider_type = django_filters.CharFilter(field_name="provider_type")
    news_source = django_filters.UUIDFilter(field_name="news_source_id")

    class Meta:
        model = ProviderHealthCheck
        fields = ("status", "provider_type", "news_source")


class PipelineRunFilter(django_filters.FilterSet):
    """Filters for pipeline run list endpoints."""

    status = django_filters.CharFilter(field_name="status")
    episode = django_filters.UUIDFilter(field_name="episode_id")

    class Meta:
        model = PipelineRun
        fields = ("status", "episode")
