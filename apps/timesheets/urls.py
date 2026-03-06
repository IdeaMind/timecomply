from django.urls import path

from . import views

app_name = "timesheets"

urlpatterns = [
    path("periods/", views.period_list, name="periods"),
    path("periods/create/", views.period_create, name="period_create"),
    path("periods/<uuid:pk>/close/", views.period_close, name="period_close"),
    path("periods/<uuid:pk>/open/", views.period_open, name="period_open"),
]
