from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.projects.models import Project

from .forms import TimeEntryForm
from .models import TimeEntry, TimePeriod, Timesheet
from .utils import calculate_next_period_dates, get_current_period

PERIOD_TYPE_CHOICES = [
    ("weekly", "Weekly (Mon-Sun)"),
    ("biweekly", "Bi-Weekly (2 weeks, Mon-Sun)"),
    ("semimonthly", "Semi-Monthly (1st-15th, 16th-EOM)"),
    ("monthly", "Monthly"),
]

_ACCESS_DENIED_MSG = "Only period managers and admins can manage pay periods."


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


@login_required
def entry_view(request):
    company = request.company
    period = get_current_period(company)

    if period is None:
        return render(request, "timesheets/entry.html", {"no_period": True})

    timesheet, _ = _get_or_create_timesheet(request.user, company, period)

    today = date.today()
    # Clamp today to within the period range
    entry_date = max(period.start_date, min(today, period.end_date))

    today_entries = timesheet.entries.filter(date=entry_date).select_related(
        "labor_category"
    )

    if request.method == "POST" and timesheet.is_editable:
        action = request.POST.get("action")

        if action == "add":
            form = TimeEntryForm(request.POST, company=company)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.timesheet = timesheet
                try:
                    entry.full_clean()
                    entry.save()
                    messages.success(request, "Time entry added.")
                except Exception as e:
                    messages.error(request, str(e))
            else:
                for field_errors in form.errors.values():
                    for error in field_errors:
                        messages.error(request, error)
            return redirect("timesheets:entry")

        elif action == "delete":
            entry_id = request.POST.get("entry_id")
            entry = get_object_or_404(TimeEntry, pk=entry_id, timesheet=timesheet)
            entry.delete()
            messages.success(request, "Time entry deleted.")
            return redirect("timesheets:entry")

    elif request.method == "POST" and not timesheet.is_editable:
        messages.error(request, "This timesheet can no longer be edited.")
        return redirect("timesheets:entry")

    form = TimeEntryForm(
        company=company,
        initial={"date": entry_date},
    )

    return render(
        request,
        "timesheets/entry.html",
        {
            "timesheet": timesheet,
            "period": period,
            "entry_date": entry_date,
            "today_entries": today_entries,
            "form": form,
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
        },
    )


@login_required
def submit_confirm(request, pk):
    company = request.company
    timesheet = get_object_or_404(
        Timesheet, pk=pk, company=company, employee=request.user
    )

    if not timesheet.is_editable:
        messages.error(request, "This timesheet has already been submitted.")
        return redirect("timesheets:weekly", pk=pk)

    if request.method == "POST":
        timesheet.status = "submitted"
        timesheet.submitted_at = timezone.now()
        timesheet.save(update_fields=["status", "submitted_at", "updated_at"])
        messages.success(request, "Timesheet submitted successfully.")
        return redirect("timesheets:weekly", pk=pk)

    return render(
        request,
        "timesheets/submit_confirm.html",
        {"timesheet": timesheet},
    )


# ---------------------------------------------------------------------------
# Period management views (unchanged from original)
# ---------------------------------------------------------------------------


@login_required
def period_list(request):
    company = request.company

    if not _can_manage_periods(request.user, company):
        messages.error(request, _ACCESS_DENIED_MSG)
        return redirect("/dashboard/")

    periods = company.time_periods.all()
    last_period = periods.first()

    suggested_start = suggested_end = None
    if last_period:
        suggested_start, suggested_end = calculate_next_period_dates(
            company, last_period
        )

    return render(
        request,
        "timesheets/periods.html",
        {
            "company": company,
            "periods": periods,
            "suggested_start": suggested_start,
            "suggested_end": suggested_end,
            "period_type": company.settings.get("period_type", "weekly"),
            "period_type_choices": PERIOD_TYPE_CHOICES,
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
    end_date_str = request.POST.get("end_date", "").strip()
    period_type = request.POST.get(
        "period_type", company.settings.get("period_type", "weekly")
    )
    auto_close_hours_raw = request.POST.get("auto_close_hours", "").strip()

    errors = []
    start_date = end_date = None

    if not start_date_str:
        errors.append("Start date is required.")
    if not end_date_str:
        errors.append("End date is required.")

    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            errors.append("Invalid date format.")

    if start_date and end_date and start_date > end_date:
        errors.append("Start date must be before end date.")

    auto_close_hours = None
    if auto_close_hours_raw:
        try:
            auto_close_hours = int(auto_close_hours_raw)
        except ValueError:
            errors.append("Auto-close hours must be a whole number.")

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
        period_type=period_type,
        auto_close_hours=auto_close_hours,
    )
    messages.success(request, f"Pay period {start_date} — {end_date} created.")
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
