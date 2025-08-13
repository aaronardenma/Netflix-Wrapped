from django.urls import path
from api.views.csv_views import QuickExtractCSVView, PriorityProcessView, GetDataView, ProcessingStatusView, StoredDataView, GetStoredDataView
from api.views.user_views import RegisterView, LoginView, LogoutView, MeView
from api.views.views import CSRFCookieView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('csv/quick-extract/', QuickExtractCSVView.as_view(), name='quick-extract'),
    path('priority-process/', PriorityProcessView.as_view(), name='priority-process'),
    path('get-data/', GetDataView.as_view(), name='get-data'),
    path('processing-status/<str:job_id>/', ProcessingStatusView.as_view(), name='processing-status'),
    path('stored-data/', StoredDataView.as_view(), name='stored-data'),
    path('get-stored-data/', GetStoredDataView.as_view(), name='get-stored-data'),

    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),       # login with username/password to get tokens
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),      # refresh access token with refresh token
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),         
    path("csrf/", CSRFCookieView.as_view(), name="csrf"),
    path("auth/me/", MeView.as_view(), name="me"),

]
