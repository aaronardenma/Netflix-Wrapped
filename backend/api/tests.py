from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient


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
