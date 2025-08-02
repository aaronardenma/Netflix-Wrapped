# views.py
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFCookieView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = get_token(request)  # This also sets the CSRF cookie
        return Response({"csrfToken": token})
        