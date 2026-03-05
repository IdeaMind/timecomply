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


def _build_tree_list(projects):
    """
    Convert a flat queryset of projects into a list of (project, depth) tuples
    in tree order (parents before children, sorted by timekeeping_code).
    """
    by_id = {p.pk: p for p in projects}
    visible_ids = set(by_id.keys())

    children_by_parent = {}
    roots = []
    for p in projects:
        if p.parent_id is None or p.parent_id not in visible_ids:
            roots.append(p)
        else:
            children_by_parent.setdefault(p.parent_id, []).append(p)

    def sort_key(p):
        parts = p.timekeeping_code.split(".")
        result = []
        for part in parts:
            try:
                result.append((0, int(part)))
            except ValueError:
                result.append((1, part))
        return result

    roots.sort(key=sort_key)
    for parent_id in children_by_parent:
        children_by_parent[parent_id].sort(key=sort_key)

    result = []

    def traverse(node, depth):
        result.append((node, depth))
        for child in children_by_parent.get(node.pk, []):
            traverse(child, depth + 1)

    for root in roots:
        traverse(root, 0)

    return result


@login_required
def project_list(request):
    company = request.company
    membership = getattr(request.user, "membership", None)
    is_admin = membership is not None and membership.role == "admin"
    show_archived = request.GET.get("show_archived") == "1"

    if is_admin:
        if show_archived:
            projects = company.projects.all()
        else:
            projects = company.projects.filter(is_archived=False)
    else:
        projects = company.projects.filter(is_archived=False)

    tree_items = _build_tree_list(list(projects))

    return render(
        request,
        "projects/list.html",
        {
            "tree_items": tree_items,
            "is_admin": is_admin,
            "company": company,
            "show_archived": show_archived,
        },
    )


@login_required
def project_create(request):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage labor categories.")
        return redirect("projects:list")

    company = request.company
    parent_choices = company.projects.filter(is_archived=False).order_by(
        "timekeeping_code"
    )

    if request.method == "POST":
        timekeeping_code = request.POST.get("timekeeping_code", "").strip()
        name = request.POST.get("name", "").strip()
        parent_id = request.POST.get("parent_id", "").strip() or None
        coa_code = request.POST.get("coa_code", "").strip()
        is_billable = request.POST.get("is_billable") == "on"
        auto_add_to_timesheet = request.POST.get("auto_add_to_timesheet") == "on"

        errors = []
        if not timekeeping_code:
            errors.append("Timekeeping code is required.")
        if not name:
            errors.append("Name is required.")

        parent = None
        if parent_id:
            try:
                parent = company.projects.get(pk=parent_id)
            except Project.DoesNotExist:
                errors.append("Selected parent category does not exist.")

        if not errors:
            if company.projects.filter(timekeeping_code=timekeeping_code).exists():
                errors.append(
                    f'A labor category with code "{timekeeping_code}" already exists.'
                )

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "projects/form.html",
                {
                    "parent_choices": parent_choices,
                    "form_data": request.POST,
                },
            )

        # Non-blocking duplicate warning: same name + same parent + same billable
        duplicate_exists = company.projects.filter(
            name=name,
            parent=parent,
            is_billable=is_billable,
        ).exists()
        if duplicate_exists:
            messages.warning(
                request,
                f'A labor category named "{name}" with the same parent and billable '
                "setting already exists. Please verify this is not a duplicate.",
            )

        try:
            project = Project.objects.create(
                company=company,
                timekeeping_code=timekeeping_code,
                name=name,
                parent=parent,
                coa_code=coa_code,
                is_billable=is_billable,
                auto_add_to_timesheet=auto_add_to_timesheet,
            )
            messages.success(
                request, f'Labor category "{timekeeping_code} — {name}" created.'
            )
            return redirect("projects:update", pk=project.pk)
        except IntegrityError:
            messages.error(
                request,
                f'A labor category with code "{timekeeping_code}" already exists.',
            )

    return render(
        request,
        "projects/form.html",
        {
            "parent_choices": parent_choices,
            "form_data": {},
        },
    )


@login_required
def project_update(request, pk):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage labor categories.")
        return redirect("projects:list")

    company = request.company
    project = get_object_or_404(Project, pk=pk, company=company)
    # Exclude this project and its descendants from the parent choices
    parent_choices = (
        company.projects.filter(is_archived=False)
        .exclude(pk=pk)
        .order_by("timekeeping_code")
    )

    if request.method == "POST":
        timekeeping_code = request.POST.get("timekeeping_code", "").strip()
        name = request.POST.get("name", "").strip()
        parent_id = request.POST.get("parent_id", "").strip() or None
        coa_code = request.POST.get("coa_code", "").strip()
        is_billable = request.POST.get("is_billable") == "on"
        auto_add_to_timesheet = request.POST.get("auto_add_to_timesheet") == "on"

        errors = []
        if not timekeeping_code:
            errors.append("Timekeeping code is required.")
        if not name:
            errors.append("Name is required.")

        parent = None
        if parent_id:
            try:
                parent = company.projects.exclude(pk=pk).get(pk=parent_id)
            except Project.DoesNotExist:
                errors.append("Selected parent category does not exist.")

        if not errors:
            if (
                company.projects.filter(timekeeping_code=timekeeping_code)
                .exclude(pk=pk)
                .exists()
            ):
                errors.append(
                    f'A labor category with code "{timekeeping_code}" already exists.'
                )

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "projects/form.html",
                {
                    "project": project,
                    "parent_choices": parent_choices,
                    "form_data": request.POST,
                },
            )

        # Non-blocking duplicate warning
        duplicate_exists = (
            company.projects.filter(
                name=name,
                parent=parent,
                is_billable=is_billable,
            )
            .exclude(pk=pk)
            .exists()
        )
        if duplicate_exists:
            messages.warning(
                request,
                f'Another labor category named "{name}" with the same parent and '
                "billable setting already exists. Verify this is not a duplicate.",
            )

        try:
            project.timekeeping_code = timekeeping_code
            project.name = name
            project.parent = parent
            project.coa_code = coa_code
            project.is_billable = is_billable
            project.auto_add_to_timesheet = auto_add_to_timesheet
            project.save()
            messages.success(
                request,
                f'Labor category "{timekeeping_code} — {name}" saved.',
            )
            return redirect("projects:update", pk=project.pk)
        except IntegrityError:
            messages.error(
                request,
                f'A labor category with code "{timekeeping_code}" already exists.',
            )

    return render(
        request,
        "projects/form.html",
        {
            "project": project,
            "parent_choices": parent_choices,
            "form_data": {
                "timekeeping_code": project.timekeeping_code,
                "name": project.name,
                "parent_id": str(project.parent_id) if project.parent_id else "",
                "coa_code": project.coa_code,
                "is_billable": project.is_billable,
                "auto_add_to_timesheet": project.auto_add_to_timesheet,
            },
        },
    )


@login_required
def project_archive(request, pk):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage labor categories.")
        return redirect("projects:list")

    company = request.company
    project = get_object_or_404(Project, pk=pk, company=company)

    if request.method == "POST":
        project.is_archived = True
        project.save(update_fields=["is_archived"])
        messages.success(
            request, f'Labor category "{project.timekeeping_code}" archived.'
        )
        return redirect("projects:list")

    return render(request, "projects/confirm_archive.html", {"project": project})


@login_required
def project_unarchive(request, pk):
    if _require_admin(request) is None:
        messages.error(request, "Only company admins can manage labor categories.")
        return redirect("projects:list")

    company = request.company
    project = get_object_or_404(Project, pk=pk, company=company)

    if request.method == "POST":
        project.is_archived = False
        project.save(update_fields=["is_archived"])
        messages.success(
            request,
            f'Labor category "{project.timekeeping_code}" reactivated.',
        )
        return redirect("projects:list")

    return render(request, "projects/confirm_unarchive.html", {"project": project})
