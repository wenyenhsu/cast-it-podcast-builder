"""Bootstrap voice profiles for TTS from environment settings."""

import logging

from django.db import transaction

from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from apps.scripts.models import Speaker
from domain.audio.dtos import VoiceInfo
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings

logger = logging.getLogger(__name__)

PRIMARY_PERSONAS = (Speaker.INTRO, Speaker.EXPERT, Speaker.BEGINNER)
PERSONA_VOICE_HINTS: dict[str, tuple[str, ...]] = {
    Speaker.INTRO: ("intro",),
    Speaker.EXPERT: ("expert",),
    Speaker.BEGINNER: ("beginner",),
}
SECONDARY_PERSONA_FALLBACK: dict[str, str] = {
    Speaker.NARRATION: Speaker.EXPERT,
    Speaker.OUTRO: Speaker.BEGINNER,
}


class VoiceSetupService:
    """Ensures persona voice mappings exist for the active TTS provider."""

    def _list_provider_voices(self, settings: TTSSettings) -> list[VoiceInfo]:
        try:
            provider = TTSProviderFactory(settings).create()
            return provider.list_voices()
        except Exception:
            logger.warning(
                "Could not list TTS voices while bootstrapping profiles",
                extra={"event": "voice_setup_list_voices_failed"},
                exc_info=True,
            )
            return []

    def _fallback_voice_id(self, settings: TTSSettings) -> str:
        if settings.default_voice:
            return settings.default_voice

        voices = self._list_provider_voices(settings)
        if voices:
            return voices[0].voice_id

        return "default"

    def _match_voice_id(
        self,
        voices: list[VoiceInfo],
        *,
        hints: tuple[str, ...],
        used_voice_ids: set[str],
    ) -> str | None:
        for voice in voices:
            if voice.voice_id in used_voice_ids:
                continue
            voice_key = f"{voice.voice_id} {voice.name}".lower()
            if any(hint in voice_key for hint in hints):
                return voice.voice_id
        return None

    def _configured_persona_voice(
        self,
        settings: TTSSettings,
        persona: str,
    ) -> str | None:
        voice_id = settings.persona_voices.get(persona, "").strip()
        return voice_id or None

    def _resolve_distinct_voice_ids(
        self,
        settings: TTSSettings,
        personas: tuple[str, ...] = PRIMARY_PERSONAS,
    ) -> dict[str, str]:
        """Pick a distinct Chatterbox voice file for each primary persona."""
        voices = self._list_provider_voices(settings)
        fallback_voice_id = self._fallback_voice_id(settings)
        assigned: dict[str, str] = {}
        used_voice_ids: set[str] = set()

        for persona in personas:
            configured = self._configured_persona_voice(settings, persona)
            if configured:
                assigned[persona] = configured
                used_voice_ids.add(configured)

        if not voices:
            for persona in personas:
                assigned.setdefault(persona, fallback_voice_id)
            return assigned

        for persona in personas:
            if persona in assigned:
                continue
            hints = PERSONA_VOICE_HINTS.get(persona, (persona,))
            matched = self._match_voice_id(
                voices,
                hints=hints,
                used_voice_ids=used_voice_ids,
            )
            if matched is not None:
                assigned[persona] = matched
                used_voice_ids.add(matched)
                continue

            for voice in voices:
                if voice.voice_id not in used_voice_ids:
                    assigned[persona] = voice.voice_id
                    used_voice_ids.add(voice.voice_id)
                    break
            else:
                assigned[persona] = voices[len(assigned) % len(voices)].voice_id

        distinct_count = len(set(assigned.values()))
        if distinct_count < len(personas):
            logger.warning(
                "Could not assign distinct Chatterbox voices for all personas",
                extra={
                    "event": "voice_setup_non_distinct_voices",
                    "persona_voices": assigned,
                    "available_voice_count": len(voices),
                },
            )

        return assigned

    @staticmethod
    def _profile_name(provider: str, persona: str) -> str:
        return f"{provider}-{persona}"

    def _auto_managed_profile_names(self, provider: str) -> set[str]:
        return {
            self._profile_name(provider, "default"),
            *(self._profile_name(provider, persona) for persona in PRIMARY_PERSONAS),
        }

    def _is_auto_managed_profile(self, provider: str, profile: VoiceProfile) -> bool:
        return profile.name in self._auto_managed_profile_names(provider)

    def _ensure_voice_profile(
        self,
        *,
        provider: str,
        persona: str,
        voice_id: str,
    ) -> tuple[VoiceProfile, bool]:
        profile, created = VoiceProfile.objects.get_or_create(
            name=self._profile_name(provider, persona),
            defaults={
                "provider": provider,
                "provider_voice_id": voice_id,
                "language": "en",
                "enabled": True,
            },
        )
        if created:
            return profile, True

        if profile.provider_voice_id != voice_id:
            profile.provider_voice_id = voice_id
            profile.save(update_fields=["provider_voice_id", "updated_at"])
            return profile, True

        return profile, False

    def _ensure_mapping(
        self,
        *,
        persona: str,
        provider: str,
        voice_profile: VoiceProfile,
    ) -> bool:
        mapping, created = PersonaVoiceMapping.objects.get_or_create(
            persona=persona,
            provider=provider,
            defaults={
                "voice_profile": voice_profile,
                "enabled": True,
            },
        )
        if created:
            return True

        if (
            mapping.voice_profile_id != voice_profile.id
            and self._is_auto_managed_profile(provider, mapping.voice_profile)
        ):
            mapping.voice_profile = voice_profile
            mapping.enabled = True
            mapping.save(
                update_fields=["voice_profile", "enabled", "updated_at"]
            )
            return True

        if not mapping.enabled:
            mapping.enabled = True
            mapping.save(update_fields=["enabled", "updated_at"])
            return True

        return False

    @transaction.atomic
    def ensure_defaults(self, settings: TTSSettings | None = None) -> int:
        """Create per-persona voice profiles and mappings when missing."""
        resolved = settings or TTSSettings.from_django_settings()
        provider = resolved.provider
        voice_ids = self._resolve_distinct_voice_ids(resolved)
        profiles_by_persona: dict[str, VoiceProfile] = {}
        updated = 0

        logger.info(
            "Bootstrapping persona voice profiles",
            extra={
                "event": "voice_setup_bootstrap",
                "provider": provider,
                "persona_voices": voice_ids,
            },
        )

        for persona in PRIMARY_PERSONAS:
            profile, changed = self._ensure_voice_profile(
                provider=provider,
                persona=persona,
                voice_id=voice_ids[persona],
            )
            profiles_by_persona[persona] = profile
            if changed:
                updated += 1
            if self._ensure_mapping(
                persona=persona,
                provider=provider,
                voice_profile=profile,
            ):
                updated += 1

        for persona, fallback_persona in SECONDARY_PERSONA_FALLBACK.items():
            fallback_profile = profiles_by_persona.get(fallback_persona)
            if fallback_profile is None:
                continue
            if self._ensure_mapping(
                persona=persona,
                provider=provider,
                voice_profile=fallback_profile,
            ):
                updated += 1

        return updated
