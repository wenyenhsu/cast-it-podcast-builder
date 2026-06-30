"""Bootstrap voice profiles for TTS from environment settings."""

import logging

from django.db import transaction

from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from apps.scripts.models import Speaker
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings

logger = logging.getLogger(__name__)


class VoiceSetupService:
    """Ensures persona voice mappings exist for the active TTS provider."""

    def _resolve_provider_voice_id(self, settings: TTSSettings) -> str:
        if settings.default_voice:
            return settings.default_voice

        try:
            provider = TTSProviderFactory(settings).create()
            voices = provider.list_voices()
            if voices:
                return voices[0].voice_id
        except Exception:
            logger.warning(
                "Could not list TTS voices while bootstrapping profiles",
                extra={"event": "voice_setup_list_voices_failed"},
                exc_info=True,
            )

        return "default"

    @transaction.atomic
    def ensure_defaults(self, settings: TTSSettings | None = None) -> int:
        """Create default voice profiles and persona mappings when missing."""
        resolved = settings or TTSSettings.from_django_settings()
        provider = resolved.provider
        voice_id = self._resolve_provider_voice_id(resolved)
        profile_name = f"{provider}-default"

        profile, _ = VoiceProfile.objects.get_or_create(
            name=profile_name,
            defaults={
                "provider": provider,
                "provider_voice_id": voice_id,
                "language": "en",
                "enabled": True,
            },
        )
        updated = 0
        if profile.provider_voice_id != voice_id:
            profile.provider_voice_id = voice_id
            profile.save(update_fields=["provider_voice_id", "updated_at"])
            updated += 1

        for persona, _label in Speaker.choices:
            mapping, created = PersonaVoiceMapping.objects.get_or_create(
                persona=persona,
                provider=provider,
                defaults={
                    "voice_profile": profile,
                    "enabled": True,
                },
            )
            if created:
                updated += 1
            elif mapping.voice_profile_id != profile.id or not mapping.enabled:
                mapping.voice_profile = profile
                mapping.enabled = True
                mapping.save(
                    update_fields=["voice_profile", "enabled", "updated_at"]
                )
                updated += 1

        return updated
