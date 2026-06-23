from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import JWTCookieAuthentication
from api.models import NetflixProfile
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
