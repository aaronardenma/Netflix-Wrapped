from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import NetflixProfile, RecommendationSet
from api.services.recommendations import RecommendationError, generate_recommendations


class Command(BaseCommand):
    help = "Refresh saved profile recommendations for stale or changed history windows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Refresh recommendation sets older than this many days.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refresh every profile with viewing history.",
        )
        parser.add_argument(
            "--profile-id",
            help="Refresh a single NetflixProfile UUID.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        profiles = NetflixProfile.objects.filter(viewing_events__isnull=False).distinct()
        if options["profile_id"]:
            profiles = profiles.filter(id=options["profile_id"])

        refreshed = 0
        skipped = 0
        failed = 0
        for profile in profiles.iterator():
            latest_set = (
                RecommendationSet.objects.filter(profile=profile)
                .order_by("-generated_at")
                .first()
            )
            should_refresh = (
                options["force"]
                or latest_set is None
                or latest_set.generated_at < cutoff
            )
            if not should_refresh:
                skipped += 1
                continue
            try:
                generate_recommendations(profile, force=True)
                refreshed += 1
            except RecommendationError as exc:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"Skipped {profile.name}: {exc}")
                )
            except Exception as exc:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed {profile.name}: {exc}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Recommendation refresh complete: {refreshed} refreshed, "
                f"{skipped} skipped, {failed} failed."
            )
        )
