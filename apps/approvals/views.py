from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    ApproverRelationship,
    BackupApprover,
    BackupApproverRule,
    apply_backup_rules_for_relationship,
    remove_rule_backups_for_relationship,
)

User = get_user_model()


def _require_admin(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or not membership.is_admin:
        messages.error(
            request, "Only company admins can configure approver relationships."
        )
        return None
    return membership


@login_required
def setup(request):
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    company = membership.company

    # All users who can act as supervisors (is_approver or is_admin)
    approver_memberships = (
        company.memberships.filter(is_active=True)
        .select_related("user")
        .order_by("user__username")
    )
    supervisor_users = [
        m.user for m in approver_memberships if m.is_approver or m.is_admin
    ]

    # All active employees
    employee_memberships = list(
        company.memberships.filter(is_employee=True, is_active=True)
        .select_related("user")
        .order_by("user__username")
    )

    # Build per-supervisor data
    supervisor_data = []
    for supervisor in supervisor_users:
        assigned_rels = list(
            ApproverRelationship.objects.filter(
                company=company, primary_approver=supervisor, is_active=True
            )
            .select_related("employee")
            .prefetch_related(
                "backup_approvers__approver", "backup_approvers__source_rule"
            )
        )
        assigned_employee_ids = {r.employee_id for r in assigned_rels}

        unassigned = [
            m for m in employee_memberships if m.user_id not in assigned_employee_ids
        ]

        rules = list(
            BackupApproverRule.objects.filter(
                company=company, supervisor=supervisor
            ).select_related("backup_approver")
        )

        supervisor_data.append(
            {
                "supervisor": supervisor,
                "assigned_rels": assigned_rels,
                "unassigned": unassigned,
                "rules": rules,
            }
        )

    return render(
        request,
        "approvals/setup.html",
        {
            "company": company,
            "supervisor_data": supervisor_data,
            "approver_users": supervisor_users,
            "employee_memberships": employee_memberships,
        },
    )


@login_required
def assign_employees(request, supervisor_pk):
    """Bulk-assign employees to a supervisor."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    supervisor = get_object_or_404(User, pk=supervisor_pk)

    sup_membership = company.memberships.filter(user=supervisor, is_active=True).first()
    if not sup_membership or not (
        sup_membership.is_approver or sup_membership.is_admin
    ):
        messages.error(request, "Selected user is not a valid supervisor.")
        return redirect("approvals:setup")

    employee_ids = request.POST.getlist("employee_ids")
    added = 0
    for emp_id in employee_ids:
        employee = User.objects.filter(pk=emp_id).first()
        if not employee:
            continue
        if not company.memberships.filter(
            user=employee, is_active=True, is_employee=True
        ).exists():
            continue
        try:
            try:
                rel = ApproverRelationship.objects.get(
                    employee=employee, company=company
                )
                rel.primary_approver = supervisor
                rel.is_active = True
                rel.save(update_fields=["primary_approver", "is_active"])
            except ApproverRelationship.DoesNotExist:
                rel = ApproverRelationship(
                    employee=employee,
                    company=company,
                    primary_approver=supervisor,
                )
                rel.full_clean()
                rel.save()
            apply_backup_rules_for_relationship(rel)
            added += 1
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))

    if added:
        sup_name = supervisor.get_full_name() or supervisor.username
        messages.success(
            request, f"{added} employee(s) assigned to {sup_name}."
        )
    return redirect("approvals:setup")


@login_required
def remove_employee(request, relationship_pk):
    """Remove an employee from their supervisor."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    rel = get_object_or_404(ApproverRelationship, pk=relationship_pk, company=company)
    remove_rule_backups_for_relationship(rel)
    emp_name = rel.employee.get_full_name() or rel.employee.username
    rel.delete()
    messages.success(request, f"Removed {emp_name} from their supervisor.")
    return redirect("approvals:setup")


@login_required
def add_backup_rule(request, supervisor_pk):
    """Add a BackupApproverRule for a supervisor and propagate to existing employees."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    supervisor = get_object_or_404(User, pk=supervisor_pk)
    backup_approver_id = request.POST.get("backup_approver_id", "").strip()

    if not backup_approver_id:
        messages.error(request, "Backup approver is required.")
        return redirect("approvals:setup")

    backup_user = get_object_or_404(User, pk=backup_approver_id)

    backup_membership = company.memberships.filter(
        user=backup_user, is_active=True
    ).first()
    if not backup_membership or not (
        backup_membership.is_approver or backup_membership.is_admin
    ):
        messages.error(request, "Selected user does not have approver permission.")
        return redirect("approvals:setup")

    rule, created = BackupApproverRule.objects.get_or_create(
        company=company,
        supervisor=supervisor,
        backup_approver=backup_user,
    )

    if not created:
        messages.warning(request, "This backup approver rule already exists.")
        return redirect("approvals:setup")

    # Propagate: create BackupApprover for all existing employees under this supervisor
    existing_rels = ApproverRelationship.objects.filter(
        company=company, primary_approver=supervisor, is_active=True
    )
    count = 0
    for rel in existing_rels:
        _, new = BackupApprover.objects.get_or_create(
            relationship=rel,
            approver=backup_user,
            defaults={"source_rule": rule},
        )
        if new:
            count += 1

    backup_name = backup_user.get_full_name() or backup_user.username
    messages.success(
        request,
        f"Rule created. {backup_name} added as backup for {count} existing employee(s).",  # noqa: E501
    )
    return redirect("approvals:setup")


@login_required
def remove_backup_rule(request, rule_pk):
    """Remove a BackupApproverRule and its inherited BackupApprover records."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    rule = get_object_or_404(BackupApproverRule, pk=rule_pk, company=company)
    BackupApprover.objects.filter(source_rule=rule).delete()
    rule.delete()
    messages.success(request, "Backup approver rule removed.")
    return redirect("approvals:setup")


@login_required
def add_backup_approver(request, relationship_pk):
    """Manually add a backup approver for a specific employee relationship."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    relationship = get_object_or_404(
        ApproverRelationship, pk=relationship_pk, company=company
    )

    backup_approver_id = request.POST.get("backup_approver_id")
    priority = request.POST.get("priority", "1")

    if not backup_approver_id:
        messages.error(request, "Backup approver is required.")
        return redirect("approvals:setup")

    try:
        priority = int(priority)
    except ValueError:
        priority = 1

    backup_user = get_object_or_404(User, pk=backup_approver_id)

    backup = BackupApprover(
        relationship=relationship,
        approver=backup_user,
        priority=priority,
        source_rule=None,
    )
    try:
        backup.full_clean()
        backup.save()
        display_name = backup_user.get_full_name() or backup_user.username
        messages.success(request, f"{display_name} added as backup approver.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("approvals:setup")


@login_required
def remove_backup_approver(request, pk):
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    backup = get_object_or_404(BackupApprover, pk=pk, relationship__company=company)
    backup.delete()
    messages.success(request, "Backup approver removed.")
    return redirect("approvals:setup")


@login_required
def assign_approver(request):
    """Single-employee assignment (kept for URL compatibility)."""
    membership = _require_admin(request)
    if membership is None:
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    employee_id = request.POST.get("employee_id")
    primary_approver_id = request.POST.get("primary_approver_id")

    if not employee_id or not primary_approver_id:
        messages.error(request, "Employee and primary approver are required.")
        return redirect("approvals:setup")

    employee = get_object_or_404(User, pk=employee_id)
    primary_approver = get_object_or_404(User, pk=primary_approver_id)

    if not company.memberships.filter(
        user=employee, is_active=True, is_employee=True
    ).exists():
        messages.error(request, "Employee is not a member of this company.")
        return redirect("approvals:setup")

    try:
        rel = ApproverRelationship.objects.get(employee=employee, company=company)
        rel.primary_approver = primary_approver
        rel.is_active = True
        created = False
    except ApproverRelationship.DoesNotExist:
        rel = ApproverRelationship(
            employee=employee,
            company=company,
            primary_approver=primary_approver,
        )
        created = True

    try:
        rel.full_clean()
        rel.save()
        apply_backup_rules_for_relationship(rel)
        action = "assigned" if created else "updated"
        display_name = employee.get_full_name() or employee.username
        messages.success(request, f"Approver {action} for {display_name}.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("approvals:setup")
