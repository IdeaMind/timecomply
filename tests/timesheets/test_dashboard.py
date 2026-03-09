"""Tests for the dashboard view and timesheet revise view."""

from datetime import date, timedelta

import pytest
from django.test import Client

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
def non_employee(company):
    user = UserFactory()
    CompanyMembershipFactory(
        user=user, company=company, is_employee=False, is_admin=True
    )
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


# ---------------------------------------------------------------------------
# Dashboard view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_requires_login():
    client = Client()
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_dashboard_employee_with_open_period(company, employee, period):
    client = Client()
    client.force_login(employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Current Pay Period" in response.content
    assert response.context["current_period"] == period


@pytest.mark.django_db
def test_dashboard_employee_no_period(company, employee):
    client = Client()
    client.force_login(employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"No active pay period" in response.content


@pytest.mark.django_db
def test_dashboard_non_employee_shows_no_timesheet_message(company, non_employee):
    client = Client()
    client.force_login(non_employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"do not have timesheet requirements" in response.content


@pytest.mark.django_db
def test_dashboard_shows_current_timesheet_status(company, employee, period):
    TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    client = Client()
    client.force_login(employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Submitted" in response.content


@pytest.mark.django_db
def test_dashboard_shows_rejected_reason_and_revise(company, employee, period):
    TimesheetFactory(
        employee=employee,
        company=company,
        period=period,
        status="rejected",
        rejection_reason="Missing charge codes.",
    )
    client = Client()
    client.force_login(employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Missing charge codes." in response.content
    assert b"Revise" in response.content


@pytest.mark.django_db
def test_dashboard_shows_today_hours(company, employee, period):
    project = ProjectFactory(company=company)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet,
        labor_category=project,
        date=date.today(),
        hours=6,
    )
    client = Client()
    client.force_login(employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"6" in response.content


@pytest.mark.django_db
def test_dashboard_non_employee_shows_admin_links(company, non_employee):
    client = Client()
    client.force_login(non_employee)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Company Settings" in response.content
    assert b"Members" in response.content


# ---------------------------------------------------------------------------
# Timesheet revise view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_revise_rejected_timesheet(company, employee, period):
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="rejected"
    )
    client = Client()
    client.force_login(employee)
    response = client.post(f"/timesheets/{timesheet.pk}/revise/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "draft"


@pytest.mark.django_db
def test_revise_non_rejected_timesheet_blocked(company, employee, period):
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    client = Client()
    client.force_login(employee)
    response = client.post(f"/timesheets/{timesheet.pk}/revise/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "submitted"


@pytest.mark.django_db
def test_revise_redirects_to_entry_view(company, employee, period):
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="rejected"
    )
    client = Client()
    client.force_login(employee)
    response = client.post(f"/timesheets/{timesheet.pk}/revise/")
    assert response.status_code == 302
    assert "/timesheets/enter/" in response["Location"]


@pytest.mark.django_db
def test_revise_non_employee_blocked(company, period):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=False)
    timesheet = TimesheetFactory(
        employee=user, company=company, period=period, status="rejected"
    )
    client = Client()
    client.force_login(user)
    response = client.post(f"/timesheets/{timesheet.pk}/revise/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "rejected"


@pytest.mark.django_db
def test_revise_other_employee_timesheet_404(company, employee, period):
    other = UserFactory()
    CompanyMembershipFactory(user=other, company=company, is_employee=True)
    timesheet = TimesheetFactory(
        employee=other, company=company, period=period, status="rejected"
    )
    client = Client()
    client.force_login(employee)
    response = client.post(f"/timesheets/{timesheet.pk}/revise/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Timesheet list scoping tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timesheet_list_scoped_to_employee(company, employee, period):
    other = UserFactory()
    CompanyMembershipFactory(user=other, company=company, is_employee=True)
    my_ts = TimesheetFactory(employee=employee, company=company, period=period)
    other_period = TimePeriodFactory(
        company=company,
        start_date=date.today() - timedelta(days=14),
        end_date=date.today() - timedelta(days=8),
        status="closed",
    )
    TimesheetFactory(employee=other, company=company, period=other_period)

    client = Client()
    client.force_login(employee)
    response = client.get("/timesheets/")
    assert response.status_code == 200
    timesheets = list(response.context["timesheets"])
    # Employee sees only their own timesheet
    assert len(timesheets) == 1
    assert timesheets[0].pk == my_ts.pk


@pytest.mark.django_db
def test_timesheet_list_shows_rejection_reason(company, employee, period):
    TimesheetFactory(
        employee=employee,
        company=company,
        period=period,
        status="rejected",
        rejection_reason="Hours do not add up.",
    )
    client = Client()
    client.force_login(employee)
    response = client.get("/timesheets/")
    assert response.status_code == 200
    assert b"Hours do not add up." in response.content
    assert b"Revise" in response.content
