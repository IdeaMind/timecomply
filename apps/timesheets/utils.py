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


def calculate_next_period_dates(company, after_period):
    """Return (start_date, end_date) for the next period after `after_period`.

    Uses the period_type from `after_period` to determine the schedule.
    """
    period_type = after_period.period_type
    start = after_period.end_date + timedelta(days=1)

    if period_type == "weekly":
        end = start + timedelta(days=6)
    elif period_type == "biweekly":
        end = start + timedelta(days=13)
    elif period_type == "semimonthly":
        # start is either the 16th (prev ended on 15th) or the 1st (prev ended at EOM)
        if start.day <= 15:
            end = date(start.year, start.month, 15)
        else:
            last_day = calendar.monthrange(start.year, start.month)[1]
            end = date(start.year, start.month, last_day)
    elif period_type == "monthly":
        # start is the 1st of next month; end is last day of that month
        last_day = calendar.monthrange(start.year, start.month)[1]
        end = date(start.year, start.month, last_day)
    else:
        raise ValueError(f"Unknown period_type: {period_type!r}")

    return start, end
