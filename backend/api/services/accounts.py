import logging

from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import NetflixProfile, Upload


logger = logging.getLogger(__name__)


def create_auth_tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh), str(refresh.access_token)


def serialize_user(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "firstName": user.firstName,
        "lastName": user.lastName,
    }


def current_password_error(user, password):
    if not password:
        return "Current password required"
    if not user.check_password(password):
        return "Current password is incorrect"
    return None


def wipe_saved_data(user):
    with transaction.atomic():
        uploads_deleted, _ = Upload.objects.filter(user=user).delete()
        profiles_deleted, _ = NetflixProfile.objects.filter(user=user).delete()
    return {
        "uploadsDeleted": uploads_deleted,
        "profilesDeleted": profiles_deleted,
    }


def delete_account(user, refresh_token=None):
    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            logger.info(
                "Refresh token was already invalid during account deletion"
            )
    user.delete()
