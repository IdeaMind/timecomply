from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.companies.models import Company
from apps.timesheets.models import TimePeriod


class Command(BaseCommand):
    help = (
        "Auto-close open periods where all timesheets are approved "
        "and company.auto_close_hours have elapsed since the last approval."
    )

    def handle(self, *args, **options):
        # Find all open periods for companies with auto_close_hours set
        companies = Company.objects.filter(
            is_active=True, auto_close_hours__isnull=False
        )

        closed_count = 0
        for company in companies:
            open_periods = TimePeriod.objects.filter(
                company=company, status="open"
            )
            for period in open_periods:
                if self._should_auto_close(period, company.auto_close_hours):
                    period.status = "closed"
                    period.save(update_fields=["status"])
                    closed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Closed period {period.start_date}–{period.end_date} "
                            f"for {company}."
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-close complete. Closed {closed_count} period(s)."
            )
        )

    def _should_auto_close(self, period, auto_close_hours):
        """Return True if the period meets all auto-close criteria."""
        end_of_period = datetime(
            period.end_date.year,
            period.end_date.month,
            period.end_date.day,
            23,
            59,
            59,
            tzinfo=dt_timezone.utc,
        )
        cutoff = timezone.now() - timedelta(hours=auto_close_hours)
        return end_of_period <= cutoff
