from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.timesheets.models import TimePeriod
from apps.timesheets.utils import calculate_next_period_dates


class Command(BaseCommand):
    help = "Create the next pay period for each active company."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-slug",
            type=str,
            help="Only run for the company with this slug.",
        )

    def handle(self, *args, **options):
        companies = Company.objects.filter(is_active=True)
        if options["company_slug"]:
            companies = companies.filter(slug=options["company_slug"])

        for company in companies:
            last_period = company.time_periods.first()  # ordered by -start_date

            if last_period is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"{company}: no periods exist — create the first"
                        " period manually."
                    )
                )
                continue

            start_date, end_date = calculate_next_period_dates(company, last_period)

            # Skip if the next period already exists (overlap check)
            if company.time_periods.filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"{company}: period {start_date}–{end_date} overlaps an"
                        " existing period, skipping."
                    )
                )
                continue

            period_type = company.settings.get("period_type", last_period.period_type)
            auto_close_hours = company.settings.get("auto_close_hours")

            TimePeriod.objects.create(
                company=company,
                start_date=start_date,
                end_date=end_date,
                period_type=period_type,
                auto_close_hours=auto_close_hours,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{company}: created period {start_date}–{end_date}"
                    f" ({period_type})."
                )
            )
