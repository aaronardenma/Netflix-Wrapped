from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import NetflixProfile, Title, Upload, ViewingEvent


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="http://localhost:3000",
)
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
