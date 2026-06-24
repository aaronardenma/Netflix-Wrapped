from datetime import timedelta
import unittest

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import (
    ExternalCatalogTitle,
    NetflixProfile,
    RecommendationFeedback,
    RecommendationSet,
    Title,
    Upload,
    ViewingEvent,
)
from .services.recommendations import generate_recommendations
from .services.recap_cache import (
    create_processing_state,
    get_processing_state,
    owner_key,
    ready_profile_years,
    result_cache_key,
    set_processing_state,
    store_upload,
)
from .services.recap_jobs import (
    process_anonymous_upload,
    process_initial_profile_year,
)
from .views.recap_views import (
    AvailableRecapsView,
    RecapDataView,
    RecapProcessingStatusView,
    SavedRecapView,
    ViewingHistoryUploadView,
    YearComparisonView,
)
from .views.recommendation_views import RecommendationFeedbackView
from .services.viewing_ingestion import clean_title, ingest_viewing_dataframe
from .services.title_metadata import apply_manual_overrides
from utils.data_analysis import enrichWithTitleMetadata, getGenreContentInsightsData


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="http://localhost:3000",
)
@unittest.skip("Email-based password reset is disabled until account recovery email is configured.")
class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="reset@example.com",
            password="OldPassword123!",
            firstName="Reset",
            lastName="User",
        )

    def test_password_reset_request_sends_email_for_existing_user(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your Netflix Wrapped password", mail.outbox[0].subject)
        self.assertIn("http://localhost:3000/auth/reset-password/", mail.outbox[0].body)

    def test_password_reset_request_is_generic_for_missing_user(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "missing@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("If an account exists", response.data["message"])

    def test_password_reset_confirm_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "password": "NewPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

    def test_password_reset_confirm_rejects_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": "bad-token",
                "password": "NewPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))


class AccountManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="account@example.com",
            password="OldPassword123!",
            firstName="Account",
            lastName="User",
        )
        self.profile = NetflixProfile.objects.create(user=self.user, name="Main")
        self.upload = Upload.objects.create(user=self.user, source_filename="history.csv")
        self.title = Title.objects.create(
            name="Sample Title",
            normalized_name="sample-title",
            media_type=Title.MediaType.MOVIE,
        )
        self.viewing_event = ViewingEvent.objects.create(
            upload=self.upload,
            profile=self.profile,
            title=self.title,
            title_raw="Sample Title",
            started_at=timezone.now(),
            duration_seconds=120,
            row_hash="a" * 64,
        )

    def test_change_password_updates_password_and_clears_cookies(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/auth/password/change/",
            {
                "currentPassword": "OldPassword123!",
                "newPassword": "NewPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_wipe_user_data_removes_saved_data_only(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/auth/account/wipe-data/",
            {"currentPassword": "OldPassword123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Upload.objects.filter(user=self.user).exists())
        self.assertFalse(NetflixProfile.objects.filter(user=self.user).exists())
        self.assertFalse(ViewingEvent.objects.filter(upload=self.upload).exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Title.objects.filter(pk=self.title.pk).exists())

    def test_delete_account_removes_user_and_clears_cookies(self):
        self.client.force_authenticate(user=self.user)
        user_id = self.user.pk

        response = self.client.post(
            "/api/auth/account/delete/",
            {"currentPassword": "OldPassword123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")
        self.assertFalse(User.objects.filter(pk=user_id).exists())
        self.assertFalse(Upload.objects.filter(user_id=user_id).exists())
        self.assertFalse(NetflixProfile.objects.filter(user_id=user_id).exists())


class ObservabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_reports_runtime_checks(self):
        response = self.client.get("/api/observability/health/")

        self.assertIn(response.status_code, (200, 503))
        self.assertIn("X-Request-ID", response)
        self.assertIn("checks", response.data)
        self.assertIn("database", response.data["checks"])
        self.assertIn("cache", response.data["checks"])
        self.assertIn("rq", response.data["checks"])

    def test_request_id_header_can_be_supplied_by_client(self):
        response = self.client.get(
            "/api/csrf/",
            HTTP_X_REQUEST_ID="request-id-test",
        )

        self.assertEqual(response["X-Request-ID"], "request-id-test")


@override_settings(TMDB_API_KEY=None)
class ProfileRecommendationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="recommend@example.com",
            password="Password123!",
            firstName="Recommend",
            lastName="User",
        )
        self.profile = NetflixProfile.objects.create(user=self.user, name="Main")
        self.upload = Upload.objects.create(
            user=self.user,
            source_filename="history.csv",
            status=Upload.Status.COMPLETED,
        )
        watched = Title.objects.create(
            name="Recent Space Drama",
            normalized_name="recent-space-drama",
            canonical_name="Recent Space Drama",
            media_type=Title.MediaType.TV_SHOW,
            genres=["Drama", "Science Fiction"],
            origin_countries=["KR"],
            original_language="ko",
            tmdb_id="10",
            metadata_confidence=0.95,
            enrichment_status=Title.EnrichmentStatus.MATCHED,
        )
        ViewingEvent.objects.create(
            upload=self.upload,
            profile=self.profile,
            title=watched,
            title_raw=watched.name,
            started_at=timezone.now() - timedelta(days=5),
            duration_seconds=7200,
            row_hash="r" * 64,
        )
        ExternalCatalogTitle.objects.create(
            source="tmdb",
            external_id="10",
            media_type=ExternalCatalogTitle.MediaType.TV,
            title="Recent Space Drama",
            overview="A Korean science fiction drama.",
            genres=["Drama", "Science Fiction"],
            origin_countries=["KR"],
            original_language="ko",
            popularity=90,
            vote_average=8.5,
            vote_count=2000,
        )
        self.unseen = ExternalCatalogTitle.objects.create(
            source="tmdb",
            external_id="20",
            media_type=ExternalCatalogTitle.MediaType.TV,
            title="Tomorrow Beyond",
            overview="A Korean crew explores a mysterious future.",
            genres=["Drama", "Science Fiction"],
            origin_countries=["KR"],
            original_language="ko",
            popularity=75,
            vote_average=8.1,
            vote_count=1200,
        )
        ExternalCatalogTitle.objects.create(
            source="tmdb",
            external_id="30",
            media_type=ExternalCatalogTitle.MediaType.MOVIE,
            title="Quiet Kitchen",
            overview="A warm documentary about chefs.",
            genres=["Documentary"],
            origin_countries=["US"],
            original_language="en",
            popularity=30,
            vote_average=7.0,
            vote_count=300,
        )

    def test_generation_recommends_unseen_catalog_titles(self):
        recommendation_set = generate_recommendations(self.profile)
        recommended_ids = set(
            recommendation_set.recommendations.values_list(
                "catalog_title__external_id", flat=True
            )
        )

        self.assertIn(self.unseen.external_id, recommended_ids)
        self.assertNotIn("10", recommended_ids)
        self.assertEqual(RecommendationSet.objects.count(), 1)
        self.assertIn("hyperparameters", recommendation_set.profile_summary)
        self.assertIn(
            "country_affinity",
            recommendation_set.recommendations.first().contributing_signals,
        )
        self.assertIn(
            "source_strength",
            recommendation_set.recommendations.first().contributing_signals,
        )

    def test_generation_reuses_current_snapshot(self):
        first = generate_recommendations(self.profile)
        second = generate_recommendations(self.profile)

        self.assertEqual(first.id, second.id)

    def test_negative_feedback_excludes_catalog_title(self):
        RecommendationFeedback.objects.create(
            profile=self.profile,
            catalog_title=self.unseen,
            action=RecommendationFeedback.Action.NOT_INTERESTED,
        )

        recommendation_set = generate_recommendations(self.profile, force=True)
        recommended_ids = set(
            recommendation_set.recommendations.values_list(
                "catalog_title__external_id", flat=True
            )
        )

        self.assertNotIn(self.unseen.external_id, recommended_ids)
        self.assertEqual(
            recommendation_set.profile_summary["feedback_counts"]["not_interested"],
            1,
        )

    def test_feedback_api_saves_profile_title_action(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/recommendations/feedback/",
            {
                "profile_name": self.profile.name,
                "media_type": self.unseen.media_type,
                "tmdb_id": self.unseen.external_id,
                "action": RecommendationFeedback.Action.SAVED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["action"], RecommendationFeedback.Action.SAVED)
        self.assertTrue(
            RecommendationFeedback.objects.filter(
                profile=self.profile,
                catalog_title=self.unseen,
                action=RecommendationFeedback.Action.SAVED,
            ).exists()
        )

    def test_api_rejects_another_users_profile(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="Password123!",
            firstName="Other",
            lastName="User",
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.post(
            "/api/recommendations/",
            {"profile_name": self.profile.name},
            format="json",
        )

        self.assertEqual(response.status_code, 404)


class RecapViewRoutingTests(TestCase):
    def test_recap_urls_resolve_to_domain_named_views(self):
        expected_views = {
            "/api/csv/quick-extract/": ViewingHistoryUploadView,
            "/api/get-data/": RecapDataView,
            "/api/processing-status/test-job/": RecapProcessingStatusView,
            "/api/stored-data/": AvailableRecapsView,
            "/api/get-stored-data/": SavedRecapView,
            "/api/compare-years/": YearComparisonView,
            "/api/recommendations/feedback/": RecommendationFeedbackView,
        }

        for path, expected_view in expected_views.items():
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class, expected_view)

    def test_missing_processing_job_returns_expired_payload(self):
        response = APIClient().get("/api/processing-status/missing-job/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "expired")
        self.assertEqual(response.data["job_id"], "missing-job")


class RecapQueueTests(TestCase):
    def setUp(self):
        cache.clear()
        self.job_id = "queue-test"
        self.owner = owner_key(None, self.job_id)
        self.profile_years = {"Main": [2024]}
        dataframe = pd.DataFrame(
            [
                {
                    "Profile Name": "Main",
                    "Start Time": "2024-01-05 20:00:00",
                    "Duration": "00:30:00",
                    "Title": "Example Movie",
                    "Attributes": "",
                    "Bookmark": "",
                    "Latest Bookmark": "",
                    "Supplemental Video Type": None,
                    "year": 2024,
                }
            ]
        )
        store_upload(
            self.owner,
            self.job_id,
            {
                "dataframe_json": dataframe.to_json(orient="records"),
                "profile_years_map": self.profile_years,
                "job_id": self.job_id,
            },
        )
        set_processing_state(
            self.job_id,
            create_processing_state(self.profile_years),
        )

    def test_queued_job_processes_upload_and_marks_it_complete(self):
        process_anonymous_upload(
            self.job_id,
            self.owner,
            self.profile_years,
        )

        state = get_processing_state(self.job_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["profiles"]["Main"]["2024"], "ready")
        self.assertEqual(state["percent"], 100)
        self.assertIsNotNone(
            cache.get(result_cache_key(self.owner, "Main", 2024))
        )

    def test_initial_processing_returns_partial_then_worker_backfills(self):
        process_initial_profile_year(
            dataframe=pd.DataFrame(
                [
                    {
                        "Profile Name": "Main",
                        "Start Time": "2024-01-05 20:00:00",
                        "Duration": "00:30:00",
                        "Title": "Example Movie",
                        "Attributes": "",
                        "Bookmark": "",
                        "Latest Bookmark": "",
                        "Supplemental Video Type": None,
                        "year": 2024,
                    }
                ]
            ),
            owner=self.owner,
            job_id=self.job_id,
            profile_name="Main",
            year=2024,
        )

        state = get_processing_state(self.job_id)
        partial_result = cache.get(result_cache_key(self.owner, "Main", 2024))
        self.assertEqual(state["profiles"]["Main"]["2024"], "partial_ready")
        self.assertEqual(ready_profile_years(state), {"Main": [2024]})
        self.assertTrue(partial_result["_partial"])
        self.assertIn("core_stats", partial_result)
        self.assertNotIn("profile_comparisons", partial_result)

        process_anonymous_upload(
            self.job_id,
            self.owner,
            self.profile_years,
        )

        full_result = cache.get(result_cache_key(self.owner, "Main", 2024))
        state = get_processing_state(self.job_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["profiles"]["Main"]["2024"], "ready")
        self.assertFalse(full_result.get("_partial", False))
        self.assertIn("profile_comparisons", full_result)


class ViewingIngestionTitleCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="viewer@example.com",
            password="Password123!",
            firstName="View",
            lastName="User",
        )

    def test_supplemental_rows_are_not_persisted(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "Profile Name": "Main",
                    "Start Time": "2024-01-01 11:59:00",
                    "Duration": "00:22:00",
                    "Title": "Avatar: The Last Airbender: Book 3: Sozin's Comet: Avatar Aang (Episode 21)",
                    "Supplemental Video Type": None,
                },
                {
                    "Profile Name": "Main",
                    "Start Time": "2024-01-01 12:00:00",
                    "Duration": "00:00:30",
                    "Title": "Season 1 Cinemagraph: The Sandman",
                    "Supplemental Video Type": "TEASER_TRAILER",
                },
                {
                    "Profile Name": "Main",
                    "Start Time": "2024-01-01 12:01:00",
                    "Duration": "00:00:30",
                    "Title": "Season 1 Character Intro Clip: Bling Empire: New York",
                    "Supplemental Video Type": "HOOK",
                },
                {
                    "Profile Name": "Main",
                    "Start Time": "2024-01-01 12:02:00",
                    "Duration": "00:00:05",
                    "Title": "Love Island Australia: Season 1_hook_primary_16x9",
                    "Supplemental Video Type": "",
                },
            ]
        )

        ingest_viewing_dataframe(self.user, dataframe, "viewing.csv")

        self.assertEqual(ViewingEvent.objects.count(), 1)
        self.assertTrue(Title.objects.filter(name="Avatar: The Last Airbender").exists())
        self.assertFalse(Title.objects.filter(name="The Sandman").exists())
        self.assertFalse(Title.objects.filter(name="Bling Empire: New York").exists())
        self.assertFalse(Title.objects.filter(name__icontains="_hook_").exists())
        self.assertFalse(Title.objects.filter(name="Season 1 Cinemagraph").exists())
        self.assertFalse(Title.objects.filter(name="Season 1 Character Intro Clip").exists())

    def test_clean_title_only_rewrites_supplemental_title_shapes_for_supplemental_rows(self):
        self.assertEqual(
            clean_title("Season 4 Teaser 3 (Cinemagraph): You", "TEASER_TRAILER"),
            "You",
        )
        self.assertEqual(
            clean_title("Trailer Park Boys: Season 12 (Trailer)", "TRAILER"),
            "Trailer Park Boys",
        )
        self.assertEqual(
            clean_title("Star Wars: Episode VIII: The Last Jedi", ""),
            "Star Wars: Episode VIII: The Last Jedi",
        )


class TitleMetadataEnrichmentTests(TestCase):
    def test_manual_override_populates_cached_title_metadata(self):
        title = Title.objects.create(name="Young Sheldon", normalized_name="young sheldon")

        apply_manual_overrides([title])

        title.refresh_from_db()
        self.assertEqual(title.canonical_name, "Young Sheldon")
        self.assertEqual(title.media_type, Title.MediaType.TV_SHOW)
        self.assertIn("TV Comedies", title.genres)
        self.assertEqual(title.origin_countries, ["US"])
        self.assertEqual(title.original_language, "en")
        self.assertEqual(title.metadata_source, "manual")
        self.assertEqual(title.enrichment_status, Title.EnrichmentStatus.MATCHED)

    def test_analytics_prefers_cached_genres_over_static_dataset(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "New Title": "Young Sheldon",
                    "Watchtime (hrs)": 1.5,
                    "Metadata Genres": ["TV Comedies"],
                    "Metadata Origin Countries": ["US"],
                    "Metadata Runtime Minutes": 22,
                    "Metadata Release Year": 2017,
                    "Type": "TV Show",
                }
            ]
        )

        enriched = enrichWithTitleMetadata(dataframe)

        self.assertEqual(enriched.iloc[0]["Primary Genre"], "TV Comedies")
        self.assertEqual(enriched.iloc[0]["Release Year"], 2017)
        self.assertEqual(enriched.iloc[0]["Metadata Country"], "United States")
        self.assertEqual(enriched.iloc[0]["Runtime Bucket"], "Short")

    def test_analytics_uses_manual_override_for_raw_csv_titles(self):
        import pandas as pd

        dataframe = pd.DataFrame([{"New Title": "Brooklyn Nine-Nine", "Watchtime (hrs)": 2.0}])

        enriched = enrichWithTitleMetadata(dataframe)

        self.assertEqual(enriched.iloc[0]["Primary Genre"], "TV Comedies")

    def test_content_insights_prefer_known_metadata_categories(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            [
                {
                    "New Title": "Known Show",
                    "Watchtime (hrs)": 1.0,
                    "Month": 1,
                    "Type": "TV Show",
                    "Rating": "TV-14",
                    "Metadata Genres": ["TV Comedies"],
                    "Metadata Origin Countries": ["US"],
                    "Metadata Runtime Minutes": 22,
                    "Metadata Release Year": 2020,
                },
                {
                    "New Title": "Unknown Show",
                    "Watchtime (hrs)": 5.0,
                    "Month": 1,
                    "Type": "Unknown",
                    "Rating": "Unknown",
                    "Metadata Genres": [],
                    "Metadata Origin Countries": [],
                    "Metadata Runtime Minutes": None,
                    "Metadata Release Year": None,
                },
            ]
        )

        insights = getGenreContentInsightsData(dataframe)

        self.assertEqual(insights["top_genre_by_month"][0]["genre"], "TV Comedies")
        self.assertEqual(insights["top_genre_by_month"][0]["month_label"], "January")
        self.assertEqual(insights["genre_watchtime"][0]["genre"], "TV Comedies")
        self.assertEqual(insights["country_watchtime"][0]["country"], "United States")
        self.assertEqual(insights["rating_watchtime"][0]["rating"], "TV-14")
        self.assertEqual(insights["release_period_watchtime"][0]["period"], "2020-2024")
