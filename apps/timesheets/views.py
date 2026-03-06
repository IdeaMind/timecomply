from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import TimePeriod
from .utils import calculate_next_period_dates

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
