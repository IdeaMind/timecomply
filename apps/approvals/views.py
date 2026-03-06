from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import ApproverRelationship, BackupApprover

User = get_user_model()


@login_required
def setup(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or not membership.is_admin:
        messages.error(
            request, "Only company admins can configure approver relationships."
        )
        return redirect("/dashboard/")

    company = membership.company
    employees = (
        company.memberships.filter(is_employee=True, is_active=True)
        .select_related("user")
        .order_by("user__username")
    )
    # Get users who can approve (is_approver or is_admin)
    approver_memberships = company.memberships.filter(is_active=True).select_related(
        "user"
    )
    approver_users = [
        m.user for m in approver_memberships if m.is_approver or m.is_admin
    ]

    relationships = (
        ApproverRelationship.objects.filter(company=company)
        .select_related("employee", "primary_approver")
        .prefetch_related("backup_approvers__approver")
    )

    return render(
        request,
        "approvals/setup.html",
        {
            "company": company,
            "employees": employees,
            "approver_users": approver_users,
            "relationships": relationships,
        },
    )


@login_required
def assign_approver(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or not membership.is_admin:
        messages.error(
            request, "Only company admins can configure approver relationships."
        )
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

    # Verify employee belongs to this company
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
        action = "assigned" if created else "updated"
        display_name = employee.get_full_name() or employee.username
        messages.success(request, f"Approver {action} for {display_name}.")
    except ValidationError as e:
        messages.error(request, str(e.message if hasattr(e, "message") else e))

    return redirect("approvals:setup")


@login_required
def add_backup_approver(request, relationship_pk):
    membership = getattr(request.user, "membership", None)
    if membership is None or not membership.is_admin:
        messages.error(
            request, "Only company admins can configure approver relationships."
        )
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
    membership = getattr(request.user, "membership", None)
    if membership is None or not membership.is_admin:
        messages.error(
            request, "Only company admins can configure approver relationships."
        )
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("approvals:setup")

    company = membership.company
    backup = get_object_or_404(BackupApprover, pk=pk, relationship__company=company)
    backup.delete()
    messages.success(request, "Backup approver removed.")
    return redirect("approvals:setup")
