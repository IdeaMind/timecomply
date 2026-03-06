from django.urls import path

from . import views

app_name = "approvals"

urlpatterns = [
    path("setup/", views.setup, name="setup"),
    # Supervisor-centric: assign employees to a supervisor
    path(
        "setup/supervisor/<int:supervisor_pk>/assign/",
        views.assign_employees,
        name="assign_employees",
    ),
    path(
        "setup/relationship/<uuid:relationship_pk>/remove/",
        views.remove_employee,
        name="remove_employee",
    ),
    # Backup approver rules
    path(
        "setup/supervisor/<int:supervisor_pk>/add-rule/",
        views.add_backup_rule,
        name="add_backup_rule",
    ),
    path(
        "setup/rule/<uuid:rule_pk>/remove/",
        views.remove_backup_rule,
        name="remove_backup_rule",
    ),
    # Manual per-relationship backup approvers
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
    # Legacy single-employee assignment
    path("setup/assign/", views.assign_approver, name="assign_approver"),
]
