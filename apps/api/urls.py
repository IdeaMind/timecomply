from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

app_name = "api"

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
]
