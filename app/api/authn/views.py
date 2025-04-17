from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class PasswordResetView(APIView):
    """
    A view to reset the user's password directly without email confirmation.
    Users provide their new password and confirm password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not new_password or not confirm_password:
            raise ValidationError(
                {"detail": "new_password and confirm_password are required."}
            )

        if new_password != confirm_password:
            raise ValidationError({"detail": "Passwords do not match."})

        user = request.user

        # Validate password using Django's validators
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            raise ValidationError({"detail": e.messages})

        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
