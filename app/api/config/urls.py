from django.contrib import admin
from django.urls import include, path
from api.views import HealthCheckView

urlpatterns = [
    path("api/", include("api.urls")),
    path("api/auth/", include("authn.urls")),
    path("admin/", admin.site.urls),
    path("health", HealthCheckView.as_view(), name="health"),
]
