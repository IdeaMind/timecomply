"""Tests for Timesheet and TimeEntry model validation and constraints."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.timesheets.models import TimeEntry, Timesheet
from tests.companies.factories import (
    CompanyFactory,
    CompanyMembershipFactory,
    UserFactory,
)
from tests.projects.factories import ProjectFactory
from tests.timesheets.factories import (
    TimeEntryFactory,
    TimePeriodFactory,
    TimesheetFactory,
)


@pytest.fixture
def company():
    return CompanyFactory()


@pytest.fixture
def employee(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    return user


@pytest.fixture
def period(company):
    today = date.today()
    return TimePeriodFactory(
        company=company,
        start_date=today,
        end_date=today + timedelta(days=6),
        status="open",
    )


@pytest.fixture
def timesheet(company, employee, period):
    return TimesheetFactory(employee=employee, company=company, period=period)


@pytest.fixture
def project(company):
    return ProjectFactory(company=company)


# ---------------------------------------------------------------------------
# Timesheet model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timesheet_unique_per_employee_per_period(company, employee, period):
    TimesheetFactory(employee=employee, company=company, period=period)
    with pytest.raises(IntegrityError):
        TimesheetFactory(employee=employee, company=company, period=period)


@pytest.mark.django_db
def test_timesheet_default_status_is_draft(company, employee, period):
    ts = TimesheetFactory(employee=employee, company=company, period=period)
    assert ts.status == "draft"


@pytest.mark.django_db
def test_timesheet_is_editable_when_draft(company, employee, period):
    ts = TimesheetFactory(
        employee=employee, company=company, period=period, status="draft"
    )
    assert ts.is_editable is True


@pytest.mark.django_db
def test_employee_cannot_edit_submitted_timesheet(company, employee, period):
    ts = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    assert ts.is_editable is False


@pytest.mark.django_db
def test_employee_cannot_edit_approved_timesheet(company, employee, period):
    ts = TimesheetFactory(
        employee=employee, company=company, period=period, status="approved"
    )
    assert ts.is_editable is False


@pytest.mark.django_db
def test_employee_cannot_edit_locked_timesheet(company, employee, period):
    ts = TimesheetFactory(
        employee=employee, company=company, period=period, status="locked"
    )
    assert ts.is_editable is False


# ---------------------------------------------------------------------------
# TimeEntry model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_time_entry_hours_non_negative(timesheet, project):
    entry = TimeEntry(
        timesheet=timesheet,
        labor_category=project,
        date=timesheet.period.start_date,
        hours=Decimal("-1.00"),
    )
    with pytest.raises(ValidationError, match="Hours cannot be negative"):
        entry.full_clean()


@pytest.mark.django_db
def test_time_entry_hours_max_24(timesheet, project):
    entry = TimeEntry(
        timesheet=timesheet,
        labor_category=project,
        date=timesheet.period.start_date,
        hours=Decimal("24.01"),
    )
    with pytest.raises(ValidationError, match="Hours cannot exceed 24"):
        entry.full_clean()


@pytest.mark.django_db
def test_time_entry_hours_exactly_24_is_valid(timesheet, project):
    entry = TimeEntry(
        timesheet=timesheet,
        labor_category=project,
        date=timesheet.period.start_date,
        hours=Decimal("24.00"),
    )
    entry.full_clean()  # Should not raise


@pytest.mark.django_db
def test_time_entry_date_within_period_enforced(timesheet, project):
    outside_date = timesheet.period.end_date + timedelta(days=1)
    entry = TimeEntry(
        timesheet=timesheet,
        labor_category=project,
        date=outside_date,
        hours=Decimal("8.00"),
    )
    with pytest.raises(
        ValidationError, match="Date must be within the timesheet period"
    ):  # noqa: E501
        entry.full_clean()


@pytest.mark.django_db
def test_time_entry_date_before_period_enforced(timesheet, project):
    outside_date = timesheet.period.start_date - timedelta(days=1)
    entry = TimeEntry(
        timesheet=timesheet,
        labor_category=project,
        date=outside_date,
        hours=Decimal("8.00"),
    )
    with pytest.raises(
        ValidationError, match="Date must be within the timesheet period"
    ):  # noqa: E501
        entry.full_clean()


@pytest.mark.django_db
def test_time_entry_valid_entry_saves(timesheet, project):
    entry = TimeEntryFactory(
        timesheet=timesheet,
        labor_category=project,
        date=timesheet.period.start_date,
        hours=Decimal("8.00"),
    )
    assert entry.pk is not None


# ---------------------------------------------------------------------------
# Auto-create timesheet on first entry
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timesheet_auto_created_on_first_entry(company, employee, period, project):
    assert not Timesheet.objects.filter(employee=employee, period=period).exists()

    timesheet, created = Timesheet.objects.get_or_create(
        employee=employee,
        period=period,
        defaults={"company": company},
    )
    assert created
    assert timesheet.status == "draft"
    assert timesheet.company == company


@pytest.mark.django_db
def test_timesheet_not_duplicated_on_second_entry(company, employee, period, project):
    Timesheet.objects.get_or_create(
        employee=employee,
        period=period,
        defaults={"company": company},
    )
    Timesheet.objects.get_or_create(
        employee=employee,
        period=period,
        defaults={"company": company},
    )
    assert Timesheet.objects.filter(employee=employee, period=period).count() == 1


# ---------------------------------------------------------------------------
# Queryset scoping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_employee_only_sees_own_timesheets(company, period):
    user1 = UserFactory()
    user2 = UserFactory()
    CompanyMembershipFactory(user=user1, company=company, is_employee=True)
    CompanyMembershipFactory(user=user2, company=company, is_employee=True)

    ts1 = TimesheetFactory(employee=user1, company=company, period=period)
    TimesheetFactory(
        employee=user2,
        company=company,
        period=TimePeriodFactory(
            company=company,
            start_date=period.start_date + timedelta(days=7),
            end_date=period.end_date + timedelta(days=7),
        ),
    )

    user1_timesheets = Timesheet.objects.filter(employee=user1, company=company)
    assert user1_timesheets.count() == 1
    assert user1_timesheets.first() == ts1


# ---------------------------------------------------------------------------
# Auto-add labor categories on new timesheet
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_auto_add_categories_pre_populated_on_new_timesheet(company, employee, period):
    auto_cat = ProjectFactory(
        company=company, auto_add_to_timesheet=True, is_archived=False
    )
    normal_cat = ProjectFactory(company=company, auto_add_to_timesheet=False)

    from datetime import timedelta

    from apps.projects.models import Project

    timesheet, created = Timesheet.objects.get_or_create(
        employee=employee,
        period=period,
        defaults={"company": company},
    )
    assert created

    auto_cats = Project.objects.filter(
        company=company, auto_add_to_timesheet=True, is_archived=False
    )
    for category in auto_cats:
        for day_offset in range((period.end_date - period.start_date).days + 1):
            entry_date = period.start_date + timedelta(days=day_offset)
            TimeEntry.objects.get_or_create(
                timesheet=timesheet,
                labor_category=category,
                date=entry_date,
                defaults={"hours": 0},
            )

    auto_entry_cats = set(timesheet.entries.values_list("labor_category", flat=True))
    assert str(auto_cat.pk) in [str(pk) for pk in auto_entry_cats]
    assert str(normal_cat.pk) not in [str(pk) for pk in auto_entry_cats]
