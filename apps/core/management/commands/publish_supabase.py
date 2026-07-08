"""Publish finished episodes (metadata + audio) to Supabase."""

from django.core.management.base import BaseCommand, CommandError

from apps.episodes.models import Episode
from services.publish.supabase_publisher import SupabasePublisher


class Command(BaseCommand):
    help = "Upload final episode audio and metadata to Supabase."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--episode-id",
            help="Publish a single episode instead of all publishable ones.",
        )

    def handle(self, *args, **options):
        try:
            publisher = SupabasePublisher()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["episode_id"]:
            episodes = list(Episode.objects.filter(id=options["episode_id"]))
            if not episodes:
                raise CommandError(f"Episode {options['episode_id']} not found.")
        else:
            episodes = publisher.publishable_episodes()

        if not episodes:
            self.stdout.write("No publishable episodes found.")
            return

        for episode in episodes:
            result = publisher.publish_episode(episode)
            self.stdout.write(
                self.style.SUCCESS(f"Published {episode.title}: {result.audio_url}")
            )
