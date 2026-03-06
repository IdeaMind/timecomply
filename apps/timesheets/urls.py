from django.urls import path

from . import views

app_name = "timesheets"

urlpatterns = [
    # Time entry
    path("timesheets/", views.timesheet_list, name="list"),
    path("timesheets/enter/", views.entry_view, name="entry"),
    path("timesheets/<uuid:pk>/", views.weekly_view, name="weekly"),
    path("timesheets/<uuid:pk>/submit/", views.submit_confirm, name="submit_confirm"),
    # Period management
    path("periods/", views.period_list, name="periods"),
    path("periods/create/", views.period_create, name="period_create"),
    path("periods/<uuid:pk>/close/", views.period_close, name="period_close"),
    path("periods/<uuid:pk>/open/", views.period_open, name="period_open"),
]
