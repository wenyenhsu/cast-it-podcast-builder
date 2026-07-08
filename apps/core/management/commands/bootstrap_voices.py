"""Bootstrap Chatterbox persona voice mappings."""

from django.core.management.base import BaseCommand

from apps.audio.models import PersonaVoiceMapping
from apps.scripts.models import Speaker
from services.audio.settings import TTSSettings
from services.audio.voice_setup import PRIMARY_PERSONAS, VoiceSetupService


class Command(BaseCommand):
    help = "Create or repair intro/expert/beginner voice mappings for Chatterbox TTS."

    def handle(self, *args, **options) -> None:
        settings = TTSSettings.from_django_settings()
        updated = VoiceSetupService().ensure_defaults(settings)

        self.stdout.write(
            self.style.SUCCESS(f"Voice bootstrap updated {updated} record(s).")
        )
        self.stdout.write("")
        self.stdout.write("Current persona mappings:")
        for persona in (*PRIMARY_PERSONAS, Speaker.NARRATION, Speaker.OUTRO):
            mapping = (
                PersonaVoiceMapping.objects.filter(
                    persona=persona,
                    provider=settings.provider,
                )
                .select_related("voice_profile")
                .first()
            )
            if mapping is None:
                self.stdout.write(f"  {persona}: (missing)")
                continue
            profile = mapping.voice_profile
            self.stdout.write(
                f"  {persona}: {profile.name} -> {profile.provider_voice_id}"
            )
