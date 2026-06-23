from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from smtplib import SMTPException

from ..authentication import JWTCookieAuthentication
from ..services.accounts import (
    create_auth_tokens,
    current_password_error,
    delete_account,
    serialize_user,
    wipe_saved_data,
)


User = get_user_model()


def set_auth_cookies(response, refresh_token, access_token):
    cookie_options = {
        "httponly": True,
        "secure": settings.SESSION_COOKIE_SECURE,
        "samesite": settings.SESSION_COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie(
        "access_token",
        access_token,
        max_age=3600,
        **cookie_options,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=7 * 24 * 3600,
        **cookie_options,
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(
        "access_token",
        path="/",
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return response


class CurrentUserView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_user(request.user))


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.is_staff:
            return Response(
                {"error": "Staff users cannot log in to this app."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh_token, access_token = create_auth_tokens(user)
        response = Response(
            {
                "message": "Login successful",
                "user": serialize_user(user),
            }
        )
        return set_auth_cookies(response, refresh_token, access_token)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        generic_response = {
            "message": "If an account exists for that email, a password reset link has been sent."
        }

        if not email:
            return Response({"error": "Email required"}, status=400)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response(generic_response)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password/{uid}/{token}"

        try:
            send_mail(
                subject="Reset your Netflix Wrapped password",
                message=(
                    "We received a request to reset your Netflix Wrapped password.\n\n"
                    f"Use this link to choose a new password:\n{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except SMTPException:
            return Response(
                {"error": "Password reset email could not be sent. Check SMTP configuration."},
                status=503,
            )

        return Response(generic_response)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")

        if not uid or not token or not password:
            return Response({"error": "UID, token, and password required"}, status=400)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            return Response({"error": "Invalid or expired reset link"}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired reset link"}, status=400)

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return Response({"error": list(exc.messages)}, status=400)

        user.set_password(password)
        user.save(update_fields=["password"])

        return clear_auth_cookies(
            Response({"message": "Password reset successful"})
        )


        
# views.py
class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("firstName")
        last_name = request.data.get("lastName")

        # Validation
        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)
        
        if not first_name or not last_name:
            return Response({"error": "First name and last name required"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=400)

        user = User.objects.create_user(
            email=email, 
            password=password,
            firstName=first_name,
            lastName=last_name,
        )
        
        refresh_token, access_token = create_auth_tokens(user)

        response = Response(
            {
                "message": "User created successfully",
                "user": serialize_user(user),
            },
            status=status.HTTP_201_CREATED,
        )
        return set_auth_cookies(response, refresh_token, access_token)


class UserLogoutView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response({"error": "No refresh token provided"}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        return clear_auth_cookies(response)


class ChangePasswordView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("currentPassword", "")
        new_password = request.data.get("newPassword", "")

        if not current_password or not new_password:
            return Response({"error": "Current and new password required"}, status=400)

        user = request.user
        if not user.check_password(current_password):
            return Response({"error": "Current password is incorrect"}, status=400)

        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response({"error": list(exc.messages)}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return clear_auth_cookies(
            Response({"message": "Password updated successfully"})
        )


class WipeUserDataView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("currentPassword", "")
        password_error = current_password_error(
            request.user,
            current_password,
        )
        if password_error:
            return Response(
                {"error": password_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deletion_counts = wipe_saved_data(request.user)

        return Response({
            "message": "Your saved data has been removed.",
            **deletion_counts,
        })


class DeleteAccountView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("currentPassword", "")
        user = request.user
        password_error = current_password_error(user, current_password)
        if password_error:
            return Response(
                {"error": password_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delete_account(user, request.COOKIES.get("refresh_token"))
        return clear_auth_cookies(
            Response({"message": "Account deleted successfully"})
        )
