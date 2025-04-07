from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


urlpatterns = [
    path("api/", include("api.urls")),
    path("api/auth/", include("authn.urls")),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", 
         SpectacularSwaggerView.as_view(url_name="schema"),
         name="schema-swagger-ui"),
    path("api/schema/redoc/",
          SpectacularRedocView.as_view(url_name="schema"),
          name="schema-redoc"),
]
