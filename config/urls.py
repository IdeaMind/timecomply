"""
URL configuration for timecomply project.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from apps.companies.views import dashboard

urlpatterns = [
    path("health/", lambda request: HttpResponse("ok")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("apps.api.urls")),
    path("companies/", include("apps.companies.urls")),
    path("dashboard/", dashboard, name="dashboard"),
    path("projects/", include("apps.projects.urls")),
    path("", include("apps.timesheets.urls")),
]
