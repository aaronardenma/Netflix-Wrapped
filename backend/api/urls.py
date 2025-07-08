from django.urls import path
from .views import UploadCSVView
from .views import ExtractCSVView


urlpatterns = [
    # path('health/', views.health_check, name='health_check'),
    # path('test-workflows/', views.test_workflows, name='test_workflows'),
    path('upload/', UploadCSVView.as_view(), name='upload-csv'),
    path('extract/', ExtractCSVView.as_view()),

]