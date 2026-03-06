import calendar
from datetime import date, timedelta


def get_current_period(company):
    """Return the currently open TimePeriod for the company, or None."""
    from apps.timesheets.models import TimePeriod

    today = date.today()
    return TimePeriod.objects.filter(
        company=company,
        status="open",
        start_date__lte=today,
        end_date__gte=today,
    ).first()


def calculate_end_date(start_date, period_type):
    """Calculate the end date for a period given start date and period type."""
    if period_type == "weekly":
        return start_date + timedelta(days=6)
    elif period_type == "biweekly":
        return start_date + timedelta(days=13)
    elif period_type == "semimonthly":
        if start_date.day <= 15:
            return date(start_date.year, start_date.month, 15)
        else:
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            return date(start_date.year, start_date.month, last_day)
    elif period_type == "monthly":
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        return date(start_date.year, start_date.month, last_day)
    else:
        raise ValueError(f"Unknown period_type: {period_type!r}")


def calculate_next_period_dates(company, after_period):
    """Return (start_date, end_date) for the next period after `after_period`.

    Uses the company's period_type setting to determine the schedule.
    """
    period_type = company.settings.get("period_type", "weekly")
    start = after_period.end_date + timedelta(days=1)
    end = calculate_end_date(start, period_type)
    return start, end


def open_due_periods(company):
    """
    Transition 'future' periods whose start_date <= today to 'open'.
    Only runs when company.auto_open is True.
    """
    if not company.auto_open:
        return

    from apps.timesheets.models import TimePeriod

    today = date.today()
    due = TimePeriod.objects.filter(
        company=company,
        status="future",
        start_date__lte=today,
    )
    due.update(status="open")
