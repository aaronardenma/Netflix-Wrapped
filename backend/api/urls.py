from django.urls import path
from api.views.recap_views import (
    AvailableRecapsView,
    RecapDataView,
    RecapProcessingStatusView,
    SavedRecapView,
    ViewingHistoryUploadView,
    YearComparisonView,
)
from api.views.user_views import (
    ChangePasswordView,
    DeleteAccountView,
    CurrentUserView,
    UserLoginView,
    UserLogoutView,
    UserRegistrationView,
    WipeUserDataView,
)
from api.views.views import CSRFCookieView
from api.views.recommendation_views import (
    ProfileRecommendationsView,
    RecommendationFeedbackView,
)
from api.views.observability_views import HealthCheckView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    path("auth/register/", UserRegistrationView.as_view(), name="register"),
    path("auth/login/", UserLoginView.as_view(), name="login"),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    # Email-based password reset is disabled until an email provider is configured.
    # path("auth/password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    # path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("auth/account/wipe-data/", WipeUserDataView.as_view(), name="wipe-account-data"),
    path("auth/account/delete/", DeleteAccountView.as_view(), name="delete-account"),

    path('csv/quick-extract/', ViewingHistoryUploadView.as_view(), name='quick-extract'),
    path('get-data/', RecapDataView.as_view(), name='get-data'),
    path('processing-status/<str:job_id>/', RecapProcessingStatusView.as_view(), name='processing-status'),
    path('stored-data/', AvailableRecapsView.as_view(), name='stored-data'),
    path('get-stored-data/', SavedRecapView.as_view(), name='get-stored-data'),
    path('compare-years/', YearComparisonView.as_view(), name='compare-years'),
    path('recommendations/', ProfileRecommendationsView.as_view(), name='recommendations'),
    path('recommendations/feedback/', RecommendationFeedbackView.as_view(), name='recommendation-feedback'),
    path('observability/health/', HealthCheckView.as_view(), name='observability-health'),

    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),       # login with username/password to get tokens
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),      # refresh access token with refresh token
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),         
    path("csrf/", CSRFCookieView.as_view(), name="csrf"),
    path("auth/me/", CurrentUserView.as_view(), name="me"),

]
