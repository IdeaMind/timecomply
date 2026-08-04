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
def test_entry_view_save_grid(company, employee, period, project):
    """Saving the grid via save_grid action creates time entries."""
    client = Client()
    client.force_login(employee)
    date_str = period.start_date.isoformat()
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "save_grid",
            "category_ids": str(project.pk),
            f"hours_{project.pk}_{date_str}": "4.00",
        },
    )
    assert response.status_code == 302
    assert TimeEntry.objects.filter(
        timesheet__employee=employee,
        labor_category=project,
        hours=Decimal("4.00"),
    ).exists()


@pytest.mark.django_db
def test_entry_view_zero_hours_deletes_entry(company, employee, period, project):
    """Setting hours to 0 in the grid removes the entry."""
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(employee=employee, company=company, period=period)
    entry = TimeEntryFactory(
        timesheet=timesheet,
        labor_category=project,
        date=period.start_date,
        hours=4,
    )
    date_str = period.start_date.isoformat()
    client.post(
        "/timesheets/enter/",
        {
            "action": "save_grid",
            "category_ids": str(project.pk),
            f"hours_{project.pk}_{date_str}": "0",
        },
    )
    assert not TimeEntry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_submitted_timesheet_cannot_add_entry(company, employee, period, project):
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    date_str = period.start_date.isoformat()
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "save_grid",
            "category_ids": str(project.pk),
            f"hours_{project.pk}_{date_str}": "4.00",
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
    """After submission, the grid save is blocked."""
    client = Client()
    client.force_login(employee)
    timesheet = TimesheetFactory(
        employee=employee, company=company, period=period, status="submitted"
    )
    date_str = period.start_date.isoformat()
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "save_grid",
            "category_ids": str(project.pk),
            f"hours_{project.pk}_{date_str}": "8.00",
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


# ---------------------------------------------------------------------------
# add_row action in entry_view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_row_adds_preset_and_redirects(company, employee, period, project):
    """POSTing add_row adds an EmployeePreset for the selected category."""
    from apps.timesheets.models import EmployeePreset

    client = Client()
    client.force_login(employee)
    response = client.post(
        "/timesheets/enter/",
        {"action": "add_row", "add_category_id": str(project.pk)},
    )
    assert response.status_code == 302
    assert EmployeePreset.objects.filter(
        company=company, employee=employee, labor_category=project
    ).exists()


@pytest.mark.django_db
def test_add_row_invalid_category_shows_error(company, employee, period):
    """POSTing add_row with a bad category ID redirects without crashing."""
    client = Client()
    client.force_login(employee)
    response = client.post(
        "/timesheets/enter/",
        {
            "action": "add_row",
            "add_category_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# preset_manage view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preset_manage_get(company, employee, project):
    """GET /timesheets/presets/ renders the preset management page."""
    client = Client()
    client.force_login(employee)
    response = client.get("/timesheets/presets/")
    assert response.status_code == 200
    assert b"Preset" in response.content


@pytest.mark.django_db
def test_preset_manage_add(company, employee, project):
    """POST add action adds a preset."""
    from apps.timesheets.models import EmployeePreset

    client = Client()
    client.force_login(employee)
    response = client.post(
        "/timesheets/presets/",
        {"action": "add", "category_id": str(project.pk)},
    )
    assert response.status_code == 302
    assert EmployeePreset.objects.filter(
        company=company, employee=employee, labor_category=project
    ).exists()


@pytest.mark.django_db
def test_preset_manage_remove(company, employee, project):
    """POST remove action deletes the preset."""
    from apps.timesheets.models import EmployeePreset

    EmployeePreset.objects.create(
        company=company, employee=employee, labor_category=project
    )
    client = Client()
    client.force_login(employee)
    response = client.post(
        "/timesheets/presets/",
        {"action": "remove", "category_id": str(project.pk)},
    )
    assert response.status_code == 302
    assert not EmployeePreset.objects.filter(
        company=company, employee=employee, labor_category=project
    ).exists()


@pytest.mark.django_db
def test_preset_manage_requires_login():
    client = Client()
    response = client.get("/timesheets/presets/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


# ---------------------------------------------------------------------------
# weekly_view — approver can view another employee's timesheet
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_weekly_view_approver_can_view_other_employee(company, period):
    """An approver can view a timesheet belonging to another employee."""
    from tests.companies.factories import CompanyMembershipFactory, UserFactory

    emp = UserFactory()
    CompanyMembershipFactory(user=emp, company=company, is_employee=True)
    approver = UserFactory()
    CompanyMembershipFactory(user=approver, company=company, is_approver=True)

    timesheet = TimesheetFactory(employee=emp, company=company, period=period)

    client = Client()
    client.force_login(approver)
    response = client.get(f"/timesheets/{timesheet.pk}/")
    assert response.status_code == 200
