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
    Users provide their new password, and confirm password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Extract new_password and confirm_password from the request data
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        # Validate that all fields are provided
        if not new_password or not confirm_password:
            raise ValidationError(
                {"detail": "new_password and confirm_password are required."}
            )

        # Validate that the passwords match
        if new_password != confirm_password:
            raise ValidationError({"detail": "Passwords do not match."})

        # Get the authenticated user
        user = request.user

        # Update the user's password
        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
