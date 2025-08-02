from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from ..authentication import JWTCookieAuthentication
from rest_framework_simplejwt.exceptions import TokenError


User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh), str(refresh.access_token)


class MeView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName
        })



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, username=email, password=password)
        if user.is_staff:
            return Response({"error": "Staff users cannot log in to this app."}, status=403)

        if user is not None:
            refresh_token, access_token = get_tokens_for_user(user)
            response = Response({
                "message": "Login successful",
                "user": {  # Include user data in response
                    "id": user.id,
                    "email": user.email
                }
            })

            # Set tokens in HttpOnly cookies
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # True for localhost/HTTP, True for production/HTTPS
                samesite="None",  # Changed from "Strict" to "None"
                max_age=3600,  # 1 hour
                path="/",  # ensure accessible on all backend routes

            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,  # True for localhost/HTTP
                samesite="None",  # Changed from "Strict"
                max_age=7 * 24 * 3600,  # 7 days
                path="/",  # ensure accessible on all backend routes

            )

            return response
        else:
            return Response({"error": "Invalid credentials"}, status=401)


        
# views.py
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("firstName")  # Note: camelCase from frontend
        last_name = request.data.get("lastName")    # Note: camelCase from frontend

        # Validation
        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)
        
        if not first_name or not last_name:
            return Response({"error": "First name and last name required"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=400)

        # Create user with all required fields
        user = User.objects.create_user(
            email=email, 
            password=password,
            firstName=first_name,  # Your model uses firstName
            lastName=last_name     # Your model uses lastName
        )
        
        refresh_token, access_token = get_tokens_for_user(user)

        response = Response({
            "message": "User created successfully",
            "user": {  # Optionally return user data for auto-login
                "id": str(user.id),
                "email": user.email,
                "firstName": user.firstName,
                "lastName": user.lastName
            }
        }, status=201)

        # Set cookies (fix secure settings for localhost)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # False for localhost, True for production
            samesite="Lax",  # Changed from "None" to "Lax"
            max_age=3600,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,  # False for localhost
            samesite="Lax",  # Changed from "None"
            max_age=7 * 24 * 3600,
        )

        return response


class LogoutView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response({"error": "No refresh token provided"}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        response = Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        response.delete_cookie(
            "access_token",
            path="/",
            samesite="None"
        )
        response.delete_cookie(
            "refresh_token",
            path="/",
            samesite="None"
        )

        return response



