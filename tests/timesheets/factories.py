import factory
from django.utils import timezone

from apps.timesheets.models import TimeEntry, TimePeriod, Timesheet
from tests.companies.factories import CompanyFactory, UserFactory
from tests.projects.factories import ProjectFactory


class TimePeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimePeriod

    company = factory.SubFactory(CompanyFactory)
    start_date = factory.LazyFunction(lambda: timezone.now().date())
    end_date = factory.LazyAttribute(
        lambda o: (
            o.start_date.replace(day=o.start_date.day + 6)
            if o.start_date.day <= 25
            else o.start_date
        )
    )
    period_type = "weekly"
    status = "open"
    auto_close_hours = None


class TimesheetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Timesheet

    employee = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    period = factory.SubFactory(
        TimePeriodFactory, company=factory.SelfAttribute("..company")
    )
    status = "draft"


class TimeEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimeEntry

    timesheet = factory.SubFactory(TimesheetFactory)
    labor_category = factory.SubFactory(
        ProjectFactory, company=factory.SelfAttribute("..timesheet.company")
    )
    date = factory.LazyAttribute(lambda o: o.timesheet.period.start_date)
    hours = factory.LazyAttribute(lambda _: 8)
    notes = ""
    is_correction = False
