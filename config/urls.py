"""
URL configuration for timecomply project.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path("health/", lambda request: HttpResponse("ok")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("apps.api.urls")),
]
