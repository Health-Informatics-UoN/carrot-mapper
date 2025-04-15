from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import AllowAny
from django.middleware.csrf import get_token
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class PasswordResetView(APIView):
    """
    A view to reset the user's password directly without email confirmation.
    Users provide their username, new password, and confirm password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        # Extract username, new_password, and confirm_password from the request data
        username = request.data.get("username")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        # Validate that all fields are provided
        if not username or not new_password or not confirm_password:
            raise ValidationError(
                {"detail": "Username, new_password, and confirm_password are required."}
            )

        # Validate that the passwords match
        if new_password != confirm_password:
            raise ValidationError({"detail": "Passwords do not match."})

        # Check if the user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Update the user's password
        user.password = make_password(new_password)
        user.save()

        return Response(
            {"detail": "Password has been reset successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


class CSRFTokenView(APIView):
    """
    A view to get the CSRF token.
    This is useful for CSRF protection in AJAX requests.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return JsonResponse({"csrfToken": get_token(request)})
