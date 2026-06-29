"""Persona to voice profile resolution."""

import logging
import uuid

from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from domain.audio.exceptions import VoiceNotFoundException

logger = logging.getLogger(__name__)


class PersonaVoiceResolver:
    """Resolves script speaker personas to database voice profiles."""

    def resolve(
        self,
        persona: str,
        *,
        provider: str,
        language: str = "en",
    ) -> VoiceProfile:
        """Return the enabled voice profile for a persona and provider."""
        mapping = (
            PersonaVoiceMapping.objects.filter(
                persona=persona,
                provider=provider,
                enabled=True,
                voice_profile__enabled=True,
            )
            .select_related("voice_profile")
            .first()
        )
        if mapping is not None:
            profile = mapping.voice_profile
            if not language or profile.language == language or profile.language == "":
                logger.debug(
                    "Persona voice resolved",
                    extra={
                        "event": "persona_voice_resolved",
                        "persona": persona,
                        "voice_profile_id": str(profile.id),
                    },
                )
                return profile

        fallback = VoiceProfile.objects.filter(
            provider=provider,
            enabled=True,
            language__in=[language, ""],
        ).first()
        if fallback is not None:
            logger.warning(
                "Persona mapping missing, using fallback voice profile",
                extra={
                    "event": "persona_voice_fallback",
                    "persona": persona,
                    "voice_profile_id": str(fallback.id),
                },
            )
            return fallback

        raise VoiceNotFoundException(
            f"No voice profile configured for persona '{persona}' "
            f"and provider '{provider}'."
        )

    def resolve_for_episode_language(
        self,
        persona: str,
        *,
        provider: str,
        episode_id: uuid.UUID,
        language: str,
    ) -> VoiceProfile:
        """Resolve persona voice with episode context for logging."""
        profile = self.resolve(persona, provider=provider, language=language)
        logger.info(
            "Voice profile selected for segment",
            extra={
                "event": "voice_profile_selected",
                "persona": persona,
                "episode_id": str(episode_id),
                "voice_profile_id": str(profile.id),
                "provider": provider,
            },
        )
        return profile
