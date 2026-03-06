from django.urls import path

from . import views

app_name = "approvals"

urlpatterns = [
    path("setup/", views.setup, name="setup"),
    path("setup/assign/", views.assign_approver, name="assign_approver"),
    path(
        "setup/<uuid:relationship_pk>/add-backup/",
        views.add_backup_approver,
        name="add_backup_approver",
    ),
    path(
        "setup/backup/<int:pk>/remove/",
        views.remove_backup_approver,
        name="remove_backup_approver",
    ),
]
