from api.views import HealthCheckView
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("", lambda r: HttpResponse(status=200), name="root"),
    path("api/", include("api.urls")),
    path("api/auth/", include("authn.urls")),
    path("admin/", admin.site.urls),
    path("health", HealthCheckView.as_view(), name="health"),
]
