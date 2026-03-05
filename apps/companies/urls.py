from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("register/", views.register_company, name="register"),
    path("settings/", views.company_settings, name="settings"),
]
