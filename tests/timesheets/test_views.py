"""Tests for timesheet entry, weekly, and submit views."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client

from apps.timesheets.models import TimeEntry
from tests.approvals.factories import ApproverRelationshipFactory
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
def project(company):
    return ProjectFactory(company=company, is_archived=False)


@pytest.fixture
def client_logged_in(employee):
    client = Client()
    client.force_login(employee)
    return client


# ---------------------------------------------------------------------------
# Entry view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_entry_view_no_period_shows_message(company, employee):
    client = Client()
    client.force_login(employee)
    response = client.get("/timesheets/enter/")
    assert response.status_code == 200
    assert b"No active pay period" in response.content


@pytest.mark.django_db
def test_entry_view_with_open_period(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    response = client.get("/timesheets/enter/")
    assert response.status_code == 200
    assert b"Enter Time" in response.content


@pytest.mark.django_db
def test_entry_view_add_entry(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "add",
            "labor_category": str(project.pk),
            "date": str(period.start_date),
            "hours": "4.00",
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert TimeEntry.objects.filter(
        timesheet__employee=employee,
        labor_category=project,
        hours=Decimal("4.00"),
    ).exists()


@pytest.mark.django_db
def test_entry_view_negative_hours_rejected(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    client.post(
        "/timesheets/enter/",
        {
            "action": "add",
            "labor_category": str(project.pk),
            "date": str(period.start_date),
            "hours": "-1",
            "notes": "",
        },
    )
    assert not TimeEntry.objects.filter(
        timesheet__employee=employee, labor_category=project
    ).exists()


@pytest.mark.django_db
def test_entry_view_excessive_hours_rejected(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    client.post(
        "/timesheets/enter/",
        {
            "action": "add",
            "labor_category": str(project.pk),
            "date": str(period.start_date),
            "hours": "25",
            "notes": "",
        },
    )
    assert not TimeEntry.objects.filter(
        timesheet__employee=employee, labor_category=project
    ).exists()


@pytest.mark.django_db
def test_entry_view_delete_entry(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    # First create a timesheet and entry
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    entry = TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "delete",
            "entry_id": str(entry.pk),
        },
    )
    assert response.status_code == 302
    assert not TimeEntry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_submitted_timesheet_cannot_add_entry(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "add",
            "labor_category": str(project.pk),
            "date": str(period.start_date),
            "hours": "4.00",
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert not TimeEntry.objects.filter(timesheet=timesheet).exists()


@pytest.mark.django_db
def test_unauthenticated_user_redirected_from_entry():
    client = Client()
    response = client.get("/timesheets/enter/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


# ---------------------------------------------------------------------------
# Weekly view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_weekly_view_shows_timesheet(company, employee, period):
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    response = client.get(f"/timesheets/{timesheet.pk}/")
    assert response.status_code == 200
    assert b"Timesheet" in response.content


@pytest.mark.django_db
def test_weekly_view_other_employee_cannot_view(company, period):
    owner = UserFactory()
    other = UserFactory()
    CompanyMembershipFactory(user=owner, company=company, is_employee=True)
    CompanyMembershipFactory(user=other, company=company, is_employee=True)
    timesheet = TimesheetFactory(employee=owner, company=company, period=period)

    client = Client()
    client.force_login(other)
    response = client.get(f"/timesheets/{timesheet.pk}/")
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# Submit confirmation view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submit_confirm_view_renders(company, employee, period, project):
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )
    response = client.get(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 200
    assert b"certify" in response.content.lower()


@pytest.mark.django_db
def test_submit_confirm_submits_timesheet(company, employee, period, project):
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )
    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "submitted"
    assert timesheet.submitted_at is not None


@pytest.mark.django_db
def test_submit_confirm_already_submitted_redirects(company, employee, period):
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    response = client.get(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# Submission workflow validation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_employee_can_submit_draft_timesheet(company, employee, period, project):
    """An employee with an approver and entries can submit a draft timesheet."""
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )

    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )

    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "submitted"


@pytest.mark.django_db
def test_submission_sets_submitted_at(company, employee, period, project):
    """Submitting a timesheet sets submitted_at to a non-null timestamp."""
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )

    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )

    client.post(f"/timesheets/{timesheet.pk}/submit/")
    timesheet.refresh_from_db()
    assert timesheet.submitted_at is not None


@pytest.mark.django_db
def test_cannot_submit_empty_timesheet(company, employee, period):
    """Submitting a timesheet with no entries is blocked."""
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )

    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)

    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "draft"


@pytest.mark.django_db
def test_cannot_submit_without_approver(company, employee, period, project):
    """Submitting without a configured approver relationship is blocked."""
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )

    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "draft"


@pytest.mark.django_db
def test_cannot_submit_already_submitted_timesheet(company, employee, period, project):
    """Double-submission of an already-submitted timesheet is blocked."""
    approver_user = UserFactory()
    CompanyMembershipFactory(user=approver_user, company=company, is_approver=True)
    ApproverRelationshipFactory(
        employee=employee, company=company, primary_approver=approver_user
    )

    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )

    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "submitted"


@pytest.mark.django_db
def test_entries_readonly_after_submission(company, employee, period, project):
    """After submission, adding new entries via the entry view is blocked."""
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "add",
            "labor_category": str(project.pk),
            "date": str(period.start_date),
            "hours": "8.00",
            "notes": "",
        },
    )
    assert response.status_code == 302
    assert not TimeEntry.objects.filter(timesheet=timesheet).exists()


@pytest.mark.django_db
def test_non_employee_cannot_submit(company, period, project):
    """A user without is_employee=True cannot submit a timesheet."""
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=False)

    client = Client()
    client.force_login(user)
    timesheet = TimesheetFactory(employee=user, company=company, period=period)
    TimeEntryFactory(
        timesheet=timesheet, labor_category=project, date=period.start_date
    )

    response = client.post(f"/timesheets/{timesheet.pk}/submit/")
    assert response.status_code == 302
    timesheet.refresh_from_db()
    assert timesheet.status == "draft"


# ---------------------------------------------------------------------------
# Timesheet list view tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timesheet_list_shows_employee_timesheets(company, employee, period):
    """The list view shows all timesheets for the logged-in employee."""
    client = Client()
    client.force_login(employee)
    TimesheetFactory(employee=employee, company=company, period=period)

    response = client.get("/timesheets/")
    assert response.status_code == 200
    assert b"My Timesheets" in response.content


@pytest.mark.django_db
def test_timesheet_list_requires_login():
    """Unauthenticated users are redirected to login."""
    client = Client()
    response = client.get("/timesheets/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
