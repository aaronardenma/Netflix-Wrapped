from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import JWTCookieAuthentication
from api.models import ExternalCatalogTitle, NetflixProfile, RecommendationFeedback
from api.services.recommendations import (
    RecommendationError,
    generate_recommendations,
    serialize_recommendation_set,
)


class ProfileRecommendationsView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile_name = str(request.data.get("profile_name") or "").strip()
        force = bool(request.data.get("refresh", False))
        if not profile_name:
            return Response(
                {"error": "profile_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = NetflixProfile.objects.get(
                user=request.user,
                name=profile_name,
            )
        except NetflixProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            recommendation_set = generate_recommendations(profile, force=force)
        except RecommendationError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            {
                "status": "ready",
                "data": serialize_recommendation_set(recommendation_set),
            }
        )


class RecommendationFeedbackView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile_name = str(request.data.get("profile_name") or "").strip()
        media_type = str(request.data.get("media_type") or "").strip()
        external_id = str(request.data.get("tmdb_id") or "").strip()
        action = str(request.data.get("action") or "").strip()

        if not profile_name or not media_type or not external_id or not action:
            return Response(
                {"error": "profile_name, media_type, tmdb_id, and action are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if action not in RecommendationFeedback.Action.values:
            return Response(
                {"error": "Unsupported feedback action"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = NetflixProfile.objects.get(user=request.user, name=profile_name)
        except NetflixProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            catalog_title = ExternalCatalogTitle.objects.get(
                source="tmdb",
                media_type=media_type,
                external_id=external_id,
            )
        except ExternalCatalogTitle.DoesNotExist:
            return Response(
                {"error": "Catalog title not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        recommendation = (
            catalog_title.recommendations.filter(recommendation_set__profile=profile)
            .order_by("-recommendation_set__generated_at")
            .first()
        )
        feedback, _ = RecommendationFeedback.objects.update_or_create(
            profile=profile,
            catalog_title=catalog_title,
            defaults={
                "recommendation": recommendation,
                "action": action,
            },
        )

        return Response(
            {
                "status": "saved",
                "data": {
                    "profile": profile.name,
                    "media_type": catalog_title.media_type,
                    "tmdb_id": catalog_title.external_id,
                    "action": feedback.action,
                    "updated_at": feedback.updated_at.isoformat(),
                },
            }
        )
