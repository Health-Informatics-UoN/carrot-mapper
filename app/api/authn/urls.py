from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import ( 
    LoginView, 
    LogoutView,
    UserDetailsView,
    PasswordResetConfirmView,
)
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from .views import DirectPasswordResetView, CSRFTokenView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="rest_register"),
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path(
        "password/reset/", DirectPasswordResetView.as_view(), name="rest_password_reset"
    ),
    path(
        "auth/password-reset-confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/refresh/", get_refresh_view().as_view(), name="token_refresh"),
    path("csrf-token/", CSRFTokenView.as_view(), name="api-csrf-token"),
]
