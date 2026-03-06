from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.approvals.models import get_approver_for
from apps.projects.models import Project

from .models import EmployeePreset, TimeEntry, TimePeriod, Timesheet
from .utils import calculate_end_date, get_current_period, open_due_periods

PERIOD_TYPE_CHOICES = [
    ("weekly", "Weekly (Mon-Sun)"),
    ("biweekly", "Bi-Weekly (2 weeks, Mon-Sun)"),
    ("semimonthly", "Semi-Monthly (1st-15th, 16th-EOM)"),
    ("monthly", "Monthly"),
]

_ACCESS_DENIED_MSG = "Only period managers and admins can manage pay periods."


def _notify_approver(timesheet, approver, request):
    """Send an email to the approver when a timesheet is submitted."""
    employee_name = timesheet.employee.get_full_name() or timesheet.employee.username
    period = timesheet.period
    subject = f"[TimeComply] Timesheet pending approval: {employee_name}"
    timesheet_url = request.build_absolute_uri(f"/timesheets/{timesheet.pk}/")
    body = (
        f"Hello {approver.get_full_name() or approver.username},\n\n"
        f"{employee_name} has submitted a timesheet for the period "
        f"{period.start_date} \u2014 {period.end_date} and it is awaiting your"
        " approval.\n\n"
        f"View timesheet: {timesheet_url}\n\n"
        f"\u2014 TimeComply"
    )
    send_mail(subject, body, None, [approver.email], fail_silently=True)


def _can_manage_periods(user, company):
    membership = getattr(user, "membership", None)
    return (
        membership is not None
        and membership.company == company
        and (membership.is_admin or membership.is_period_manager)
    )


def _get_or_create_timesheet(user, company, period):
    """Get or create a timesheet; auto-populate auto_add categories on creation."""
    timesheet, created = Timesheet.objects.get_or_create(
        employee=user,
        period=period,
        defaults={"company": company},
    )
    if created:
        auto_categories = Project.objects.filter(
            company=company,
            auto_add_to_timesheet=True,
            is_archived=False,
        )
        for category in auto_categories:
            for day_offset in range((period.end_date - period.start_date).days + 1):
                entry_date = period.start_date + timedelta(days=day_offset)
                TimeEntry.objects.get_or_create(
                    timesheet=timesheet,
                    labor_category=category,
                    date=entry_date,
                    defaults={"hours": 0},
                )
    return timesheet, created


def _build_grid(timesheet, period_dates, company, user):
    """Build grid rows for the weekly entry view."""
    entries = timesheet.entries.select_related("labor_category")

    # Build entry map: {category: {date: entry}}
    entry_map = {}
    for entry in entries:
        entry_map.setdefault(entry.labor_category, {})[entry.date] = entry

    # Categories already in entries
    entry_cats = set(entry_map.keys())

    # Preset categories (always show as rows)
    preset_cat_ids = set(
        EmployeePreset.objects.filter(company=company, employee=user).values_list(
            "labor_category", flat=True
        )
    )
    preset_projects = set(
        Project.objects.filter(pk__in=preset_cat_ids, is_archived=False)
    )

    all_cats = sorted(
        entry_cats | preset_projects,
        key=lambda c: c.timekeeping_code,
    )

    grid = []
    for cat in all_cats:
        cells = [
            {"date": d, "entry": entry_map.get(cat, {}).get(d)}
            for d in period_dates
        ]
        row_total = sum(
            c["entry"].hours
            for c in cells
            if c["entry"] is not None and c["entry"].hours is not None
        )
        grid.append(
            {
                "category": cat,
                "cells": cells,
                "total": row_total,
            }
        )

    col_totals = []
    for d in period_dates:
        col_total = sum(
            entry_map.get(cat, {}).get(d).hours or 0
            for cat in all_cats
            if entry_map.get(cat, {}).get(d)
        )
        col_totals.append(col_total)

    grand_total = sum(col_totals)
    return grid, col_totals, grand_total, all_cats


@login_required
def entry_view(request):
    company = request.company
    open_due_periods(company)

    # Determine which period to display
    period_id = request.GET.get("period")
    if period_id:
        period = get_object_or_404(TimePeriod, pk=period_id, company=company)
    else:
        period = get_current_period(company)

    if period is None:
        return render(request, "timesheets/entry.html", {"no_period": True})

    timesheet, _ = _get_or_create_timesheet(request.user, company, period)

    # A period is read-only if it's closed/future or the timesheet is not editable
    read_only = period.status in ("closed", "future") or not timesheet.is_editable

    period_dates = [
        period.start_date + timedelta(days=i)
        for i in range((period.end_date - period.start_date).days + 1)
    ]

    if request.method == "POST" and not read_only:
        action = request.POST.get("action")

        if action == "save_grid":
            all_category_ids = request.POST.getlist("category_ids")
            for cat_id in all_category_ids:
                try:
                    category = company.projects.get(pk=cat_id, is_archived=False)
                except Project.DoesNotExist:
                    continue
                for d in period_dates:
                    field_name = f"hours_{cat_id}_{d.isoformat()}"
                    raw = request.POST.get(field_name, "").strip()
                    if not raw:
                        TimeEntry.objects.filter(
                            timesheet=timesheet, labor_category=category, date=d
                        ).delete()
                        continue
                    try:
                        hours = float(raw)
                    except ValueError:
                        continue
                    if hours == 0:
                        TimeEntry.objects.filter(
                            timesheet=timesheet, labor_category=category, date=d
                        ).delete()
                    else:
                        TimeEntry.objects.update_or_create(
                            timesheet=timesheet,
                            labor_category=category,
                            date=d,
                            defaults={"hours": hours},
                        )
            messages.success(request, "Timesheet saved.")
            return redirect(f"{request.path}?period={period.pk}")

        elif action == "add_row":
            cat_id = request.POST.get("add_category_id", "").strip()
            if cat_id:
                try:
                    category = company.projects.get(pk=cat_id, is_archived=False)
                    EmployeePreset.objects.get_or_create(
                        company=company,
                        employee=request.user,
                        labor_category=category,
                    )
                    messages.success(
                        request,
                        f'"{category.timekeeping_code} — {category.name}" added to your timesheet.',  # noqa: E501
                    )
                except Project.DoesNotExist:
                    messages.error(request, "Selected labor category not found.")
            return redirect(f"{request.path}?period={period.pk}")

    elif request.method == "POST" and read_only:
        messages.error(request, "This timesheet period cannot be edited.")
        return redirect(f"{request.path}?period={period.pk}")

    grid, col_totals, grand_total, grid_cats = _build_grid(
        timesheet, period_dates, company, request.user
    )

    # Available categories for Add Row (not already in grid)
    grid_cat_ids = {c.pk for c in grid_cats}
    available_cats = list(
        company.projects.filter(is_archived=False)
        .exclude(pk__in=grid_cat_ids)
        .order_by("timekeeping_code")
    )

    # Navigation: previous/current/next periods
    prev_period = (
        company.time_periods.filter(end_date__lt=period.start_date)
        .order_by("-start_date")
        .first()
    )
    next_period = (
        company.time_periods.filter(start_date__gt=period.end_date)
        .order_by("start_date")
        .first()
    )
    current_period = get_current_period(company)

    membership = getattr(request.user, "membership", None)
    can_submit = (
        timesheet.employee == request.user
        and timesheet.is_editable
        and period.status == "open"
        and membership is not None
        and membership.is_employee
    )

    return render(
        request,
        "timesheets/entry.html",
        {
            "timesheet": timesheet,
            "period": period,
            "period_dates": period_dates,
            "grid": grid,
            "col_totals": col_totals,
            "grand_total": grand_total,
            "read_only": read_only,
            "available_cats": available_cats,
            "prev_period": prev_period,
            "next_period": next_period,
            "current_period": current_period,
            "can_submit": can_submit,
        },
    )


@login_required
def preset_manage(request):
    company = request.company
    employee = request.user

    all_categories = company.projects.filter(is_archived=False).order_by(
        "timekeeping_code"
    )
    presets = EmployeePreset.objects.filter(
        company=company, employee=employee
    ).select_related("labor_category")
    preset_ids = {p.labor_category_id for p in presets}

    if request.method == "POST":
        action = request.POST.get("action")
        cat_id = request.POST.get("category_id", "").strip()

        if action == "add" and cat_id:
            try:
                category = company.projects.get(pk=cat_id, is_archived=False)
                EmployeePreset.objects.get_or_create(
                    company=company, employee=employee, labor_category=category
                )
                messages.success(request, f'"{category}" added to presets.')
            except Project.DoesNotExist:
                messages.error(request, "Category not found.")

        elif action == "remove" and cat_id:
            EmployeePreset.objects.filter(
                company=company, employee=employee, labor_category_id=cat_id
            ).delete()
            messages.success(request, "Preset removed.")

        return redirect("timesheets:preset_manage")

    available = [c for c in all_categories if c.pk not in preset_ids]

    return render(
        request,
        "timesheets/presets.html",
        {
            "presets": presets,
            "available_categories": available,
        },
    )


@login_required
def weekly_view(request, pk):
    company = request.company
    timesheet = get_object_or_404(Timesheet, pk=pk, company=company)

    # Only the employee or an admin/approver can view
    membership = getattr(request.user, "membership", None)
    if timesheet.employee != request.user and not (
        membership and (membership.is_admin or membership.is_approver)
    ):
        messages.error(request, "You do not have permission to view this timesheet.")
        return redirect("timesheets:entry")

    period = timesheet.period
    period_dates = [
        period.start_date + timedelta(days=i)
        for i in range((period.end_date - period.start_date).days + 1)
    ]

    entries = timesheet.entries.select_related("labor_category").order_by(
        "labor_category__timekeeping_code", "date"
    )

    # Build a set of labor categories used in this timesheet
    categories = list({e.labor_category for e in entries})
    categories.sort(key=lambda c: c.timekeeping_code)

    # Build grid: {category: {date: entry_or_none}}
    entry_map = {}
    for entry in entries:
        entry_map.setdefault(entry.labor_category, {})[entry.date] = entry

    grid = []
    for category in categories:
        row = {
            "category": category,
            "entries": [entry_map.get(category, {}).get(d) for d in period_dates],
            "total": sum(
                (entry_map.get(category, {}).get(d).hours or 0)
                for d in period_dates
                if entry_map.get(category, {}).get(d)
            ),
        }
        grid.append(row)

    # Column totals
    col_totals = []
    for d in period_dates:
        col_total = sum(
            entry_map.get(cat, {}).get(d).hours or 0
            for cat in categories
            if entry_map.get(cat, {}).get(d)
        )
        col_totals.append(col_total)

    grand_total = sum(col_totals)

    can_submit = (
        timesheet.employee == request.user
        and timesheet.is_editable
        and membership is not None
        and membership.is_employee
    )

    return render(
        request,
        "timesheets/weekly.html",
        {
            "timesheet": timesheet,
            "period": period,
            "period_dates": period_dates,
            "grid": grid,
            "col_totals": col_totals,
            "grand_total": grand_total,
            "can_submit": can_submit,
        },
    )


@login_required
def submit_confirm(request, pk):
    company = request.company
    timesheet = get_object_or_404(
        Timesheet, pk=pk, company=company, employee=request.user
    )

    membership = getattr(request.user, "membership", None)
    if not membership or not membership.is_employee:
        messages.error(request, "Only employees can submit timesheets.")
        return redirect("timesheets:entry")

    if not timesheet.is_editable:
        messages.error(request, "This timesheet has already been submitted.")
        return redirect("timesheets:entry")

    if not timesheet.entries.exists():
        messages.error(request, "Cannot submit an empty timesheet.")
        return redirect("timesheets:entry")

    approver = get_approver_for(request.user, company)
    if not approver:
        messages.error(
            request,
            "No approver configured. Contact your administrator.",
        )
        return redirect("timesheets:entry")

    if request.method == "POST":
        timesheet.status = "submitted"
        timesheet.submitted_at = timezone.now()
        timesheet.save(update_fields=["status", "submitted_at", "updated_at"])
        _notify_approver(timesheet, approver, request)
        messages.success(request, "Timesheet submitted successfully.")
        return redirect("timesheets:entry")

    return render(
        request,
        "timesheets/submit_confirm.html",
        {"timesheet": timesheet},
    )


@login_required
def timesheet_list(request):
    company = request.company
    timesheets = (
        Timesheet.objects.filter(employee=request.user, company=company)
        .select_related("period")
        .order_by("-period__start_date")
    )
    return render(
        request,
        "timesheets/list.html",
        {"timesheets": timesheets},
    )


# ---------------------------------------------------------------------------
# Period management views
# ---------------------------------------------------------------------------


@login_required
def period_list(request):
    company = request.company
    open_due_periods(company)

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    periods = company.time_periods.all()
    last_period = periods.first()

    suggested_start = None
    if last_period:
        from .utils import calculate_next_period_dates

        suggested_start, _ = calculate_next_period_dates(company, last_period)

    period_type = company.settings.get("period_type", "weekly")
    period_type_label = dict(PERIOD_TYPE_CHOICES).get(period_type, period_type)

    return render(
        request,
        "timesheets/periods.html",
        {
            "company": company,
            "periods": periods,
            "suggested_start": suggested_start,
            "period_type": period_type,
            "period_type_label": period_type_label,
        },
    )


@login_required
def period_create(request):
    company = request.company

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    if request.method != "POST":
        return redirect("timesheets:periods")

    start_date_str = request.POST.get("start_date", "").strip()
    period_type = company.settings.get("period_type", "weekly")

    errors = []
    start_date = end_date = None

    if not start_date_str:
        errors.append("Start date is required.")
    else:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = calculate_end_date(start_date, period_type)
        except ValueError as exc:
            errors.append(f"Invalid date: {exc}")

    if start_date and end_date and not errors:
        overlapping = company.time_periods.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if overlapping:
            errors.append("This period overlaps with an existing period.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect("timesheets:periods")

    TimePeriod.objects.create(
        company=company,
        start_date=start_date,
        end_date=end_date,
        status="future",
    )
    messages.success(
        request,
        f"Pay period {start_date} — {end_date} created (status: Future).",
    )
    return redirect("timesheets:periods")


@login_required
def period_close(request, pk):
    company = request.company

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    period = get_object_or_404(TimePeriod, pk=pk, company=company)

    if request.method == "POST":
        if period.status == "closed":
            messages.error(request, "This period is already closed.")
        else:
            period.status = "closed"
            period.save(update_fields=["status"])
            messages.success(
                request, f"Period {period.start_date} — {period.end_date} closed."
            )

    return redirect("timesheets:periods")


@login_required
def period_open(request, pk):
    company = request.company

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    period = get_object_or_404(TimePeriod, pk=pk, company=company)

    if request.method == "POST":
        if period.status == "open":
            messages.error(request, "This period is already open.")
        else:
            period.status = "open"
            period.save(update_fields=["status"])
            messages.success(
                request,
                f"Period {period.start_date} — {period.end_date} reopened.",
            )

    return redirect("timesheets:periods")


@login_required
def period_delete(request, pk):
    company = request.company

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    period = get_object_or_404(TimePeriod, pk=pk, company=company)

    if request.method == "POST":
        if Timesheet.objects.filter(period=period).exists():
            messages.error(
                request,
                f"Cannot delete period {period.start_date} — {period.end_date} "
                "because it has timesheets. Close it instead.",
            )
        else:
            period.delete()
            messages.success(
                request,
                f"Period {period.start_date} — {period.end_date} deleted.",
            )
        return redirect("timesheets:periods")

    has_timesheets = Timesheet.objects.filter(period=period).exists()
    return render(
        request,
        "timesheets/confirm_delete_period.html",
        {"period": period, "has_timesheets": has_timesheets},
    )
