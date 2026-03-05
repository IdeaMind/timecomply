from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .models import Project


def _require_admin(request):
    """Return the membership if user is a company admin, else None."""
    membership = getattr(request.user, "membership", None)
    if membership is None or membership.role != "admin":
        return None
    return membership


@login_required
def project_list(request):
    company = request.company
    membership = getattr(request.user, "membership", None)
    is_admin = membership is not None and membership.role == "admin"

    if is_admin:
        projects = company.projects.all().order_by("code")
    else:
        projects = company.projects.filter(is_active=True).order_by("code")

    return render(
        request,
        "projects/list.html",
        {
            "projects": projects,
            "is_admin": is_admin,
            "company": company,
        },
    )


@login_required
def project_create(request):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage projects.")
        return redirect("projects:list")

    company = request.company
    contract_type_choices = Project.CONTRACT_TYPE_CHOICES

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        name = request.POST.get("name", "").strip()
        contract_type = request.POST.get("contract_type", "")
        is_billable = request.POST.get("is_billable") == "on"

        errors = []
        if not code:
            errors.append("Project code is required.")
        if not name:
            errors.append("Project name is required.")
        if contract_type not in dict(Project.CONTRACT_TYPE_CHOICES):
            errors.append("Please select a valid contract type.")

        if not errors:
            if company.projects.filter(code=code).exists():
                errors.append(f'A project with code "{code}" already exists.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "projects/form.html",
                {
                    "contract_type_choices": contract_type_choices,
                    "form_data": request.POST,
                },
            )

        try:
            Project.objects.create(
                company=company,
                code=code,
                name=name,
                contract_type=contract_type,
                is_billable=is_billable,
            )
            messages.success(request, f'Project "{code} — {name}" created.')
            return redirect("projects:list")
        except IntegrityError:
            messages.error(request, f'A project with code "{code}" already exists.')

    return render(
        request,
        "projects/form.html",
        {
            "contract_type_choices": contract_type_choices,
            "form_data": {},
        },
    )


@login_required
def project_update(request, pk):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage projects.")
        return redirect("projects:list")

    company = request.company
    project = get_object_or_404(Project, pk=pk, company=company)
    contract_type_choices = Project.CONTRACT_TYPE_CHOICES

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        name = request.POST.get("name", "").strip()
        contract_type = request.POST.get("contract_type", "")
        is_billable = request.POST.get("is_billable") == "on"

        errors = []
        if not code:
            errors.append("Project code is required.")
        if not name:
            errors.append("Project name is required.")
        if contract_type not in dict(Project.CONTRACT_TYPE_CHOICES):
            errors.append("Please select a valid contract type.")

        if not errors and company.projects.filter(code=code).exclude(pk=pk).exists():
            errors.append(f'A project with code "{code}" already exists.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "projects/form.html",
                {
                    "project": project,
                    "contract_type_choices": contract_type_choices,
                    "form_data": request.POST,
                },
            )

        try:
            project.code = code
            project.name = name
            project.contract_type = contract_type
            project.is_billable = is_billable
            project.save()
            messages.success(request, f'Project "{code} — {name}" updated.')
            return redirect("projects:list")
        except IntegrityError:
            messages.error(request, f'A project with code "{code}" already exists.')

    return render(
        request,
        "projects/form.html",
        {
            "project": project,
            "contract_type_choices": contract_type_choices,
            "form_data": {
                "code": project.code,
                "name": project.name,
                "contract_type": project.contract_type,
                "is_billable": project.is_billable,
            },
        },
    )


@login_required
def project_deactivate(request, pk):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage projects.")
        return redirect("projects:list")

    company = request.company
    project = get_object_or_404(Project, pk=pk, company=company)

    if request.method == "POST":
        project.is_active = False
        project.save(update_fields=["is_active"])
        messages.success(request, f'Project "{project.code}" deactivated.')
        return redirect("projects:list")

    return render(request, "projects/confirm_deactivate.html", {"project": project})
