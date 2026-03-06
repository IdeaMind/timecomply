from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.timesheets.models import TimePeriod


class Command(BaseCommand):
    help = (
        "Auto-close open periods where all timesheets are approved "
        "and auto_close_hours have elapsed since the last approval."
    )

    def handle(self, *args, **options):
        open_periods = TimePeriod.objects.filter(
            status="open",
            auto_close_hours__isnull=False,
        ).select_related("company")

        closed_count = 0
        for period in open_periods:
            if self._should_auto_close(period):
                period.status = "closed"
                period.save(update_fields=["status"])
                closed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Closed period {period.start_date}–{period.end_date} "
                        f"for {period.company}."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Auto-close complete. Closed {closed_count} period(s).")
        )

    def _should_auto_close(self, period):
        """Return True if the period meets all auto-close criteria.

        Criteria:
        1. All timesheets in the period are approved.
        2. auto_close_hours have elapsed since the last timesheet approval.

        NOTE: When the Timesheet model is added, update this method to query
        actual timesheet approval status and last_approved_at timestamps.
        For now, we use the period's end_date as a proxy: auto-close if
        auto_close_hours have elapsed since midnight at the end of the period.
        """
        end_of_period = datetime(
            period.end_date.year,
            period.end_date.month,
            period.end_date.day,
            23,
            59,
            59,
            tzinfo=dt_timezone.utc,
        )
        cutoff = timezone.now() - timedelta(hours=period.auto_close_hours)
        return end_of_period <= cutoff
