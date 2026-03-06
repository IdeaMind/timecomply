"""Tests for TimePeriod model, utilities, management commands, and views."""

from datetime import date, datetime
from datetime import timezone as dt_tz
from unittest.mock import patch

import django.utils.timezone as tz_module
import pytest
from django.core.management import call_command
from django.test import Client

from apps.timesheets.models import TimePeriod
from apps.timesheets.utils import calculate_next_period_dates, get_current_period
from tests.companies.factories import (
    CompanyFactory,
    CompanyMembershipFactory,
    UserFactory,
)


@pytest.fixture
def company():
    return CompanyFactory(settings={"period_type": "weekly"})


@pytest.fixture
def admin_user(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_admin=True)
    return user


@pytest.fixture
def period_manager_user(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_period_manager=True)
    return user


@pytest.fixture
def employee_user(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    return user


def make_period(company, start, end, status="open"):
    return TimePeriod.objects.create(
        company=company,
        start_date=start,
        end_date=end,
        status=status,
    )


# ---------------------------------------------------------------------------
# Period type calculation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_weekly_next_period_calculation(company):
    company.settings = {**company.settings, "period_type": "weekly"}
    company.save()
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 12))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 1, 13)
    assert end == date(2025, 1, 19)


@pytest.mark.django_db
def test_biweekly_next_period_calculation(company):
    company.settings = {**company.settings, "period_type": "biweekly"}
    company.save()
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 19))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 1, 20)
    assert end == date(2025, 2, 2)


@pytest.mark.django_db
def test_semimonthly_period_calculations_first_half(company):
    company.settings = {**company.settings, "period_type": "semimonthly"}
    company.save()
    period = make_period(company, date(2025, 1, 1), date(2025, 1, 15))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 1, 16)
    assert end == date(2025, 1, 31)


@pytest.mark.django_db
def test_semimonthly_period_calculations_second_half(company):
    company.settings = {**company.settings, "period_type": "semimonthly"}
    company.save()
    period = make_period(company, date(2025, 1, 16), date(2025, 1, 31))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 2, 1)
    assert end == date(2025, 2, 15)


@pytest.mark.django_db
def test_semimonthly_period_feb_leap_year(company):
    company.settings = {**company.settings, "period_type": "semimonthly"}
    company.save()
    period = make_period(company, date(2024, 2, 1), date(2024, 2, 15))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2024, 2, 16)
    assert end == date(2024, 2, 29)


@pytest.mark.django_db
def test_semimonthly_period_feb_non_leap_year(company):
    company.settings = {**company.settings, "period_type": "semimonthly"}
    company.save()
    period = make_period(company, date(2025, 2, 1), date(2025, 2, 15))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 2, 16)
    assert end == date(2025, 2, 28)


@pytest.mark.django_db
def test_monthly_period_calculations(company):
    company.settings = {**company.settings, "period_type": "monthly"}
    company.save()
    period = make_period(company, date(2025, 1, 1), date(2025, 1, 31))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 2, 1)
    assert end == date(2025, 2, 28)


@pytest.mark.django_db
def test_monthly_period_december_to_january(company):
    company.settings = {**company.settings, "period_type": "monthly"}
    company.save()
    period = make_period(company, date(2024, 12, 1), date(2024, 12, 31))
    start, end = calculate_next_period_dates(company, period)
    assert start == date(2025, 1, 1)
    assert end == date(2025, 1, 31)


# ---------------------------------------------------------------------------
# Overlap validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_overlapping_period_rejected(company, admin_user):
    make_period(company, date(2025, 1, 6), date(2025, 1, 12))
    client = Client()
    client.force_login(admin_user)
    response = client.post(
        "/periods/create/",
        {
            "start_date": "2025-01-10",
        },
    )
    # Should redirect back to list with an error message
    assert response.status_code == 302
    # Confirm no second period was created
    assert TimePeriod.objects.filter(company=company).count() == 1


@pytest.mark.django_db
def test_non_overlapping_period_accepted(company, admin_user):
    make_period(company, date(2025, 1, 6), date(2025, 1, 12))
    client = Client()
    client.force_login(admin_user)
    response = client.post(
        "/periods/create/",
        {
            "start_date": "2025-01-13",
        },
    )
    assert response.status_code == 302
    assert TimePeriod.objects.filter(company=company).count() == 2


# ---------------------------------------------------------------------------
# get_current_period utility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_current_period_returns_open_period(company):
    today = date.today()
    period = make_period(company, today, today, status="open")
    result = get_current_period(company)
    assert result == period


@pytest.mark.django_db
def test_get_current_period_ignores_closed(company):
    today = date.today()
    make_period(company, today, today, status="closed")
    result = get_current_period(company)
    assert result is None


@pytest.mark.django_db
def test_get_current_period_returns_none_when_no_periods(company):
    assert get_current_period(company) is None


# ---------------------------------------------------------------------------
# Auto-close management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_auto_close_triggers_after_all_approved(company):
    company.auto_close_hours = 24
    company.save()
    period = make_period(company, date(2025, 1, 1), date(2025, 1, 7), status="open")
    future_now = datetime(2025, 1, 10, 12, 0, 0, tzinfo=dt_tz.utc)
    with patch.object(tz_module, "now", return_value=future_now):
        call_command("auto_close_periods", verbosity=0)

    period.refresh_from_db()
    assert period.status == "closed"


@pytest.mark.django_db
def test_auto_close_does_not_trigger_if_timesheets_pending(company):
    company.auto_close_hours = 24
    company.save()
    period = make_period(company, date(2025, 1, 1), date(2025, 1, 7), status="open")
    # Only 1 hour after end of period — not enough
    slightly_after = datetime(2025, 1, 8, 1, 0, 0, tzinfo=dt_tz.utc)
    with patch.object(tz_module, "now", return_value=slightly_after):
        call_command("auto_close_periods", verbosity=0)

    period.refresh_from_db()
    assert period.status == "open"


@pytest.mark.django_db
def test_auto_close_skips_periods_without_auto_close_hours(company):
    # company.auto_close_hours is None by default — nothing should close
    period = make_period(company, date(2025, 1, 1), date(2025, 1, 7), status="open")
    call_command("auto_close_periods", verbosity=0)
    period.refresh_from_db()
    assert period.status == "open"


# ---------------------------------------------------------------------------
# open_next_period management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_open_next_period_creates_next_weekly(company):
    make_period(company, date(2025, 1, 6), date(2025, 1, 12))
    call_command("open_next_period", verbosity=0)
    assert TimePeriod.objects.filter(company=company).count() == 2
    new_period = (
        TimePeriod.objects.filter(company=company).order_by("start_date").last()
    )
    assert new_period.start_date == date(2025, 1, 13)
    assert new_period.end_date == date(2025, 1, 19)


@pytest.mark.django_db
def test_open_next_period_skips_if_overlap_exists(company):
    """Command skips if the calculated next period overlaps an existing one."""
    make_period(company, date(2025, 1, 13), date(2025, 1, 19))
    # Older period whose end_date falls inside the calculated next range (Jan 20-26)
    make_period(company, date(2024, 12, 30), date(2025, 1, 22))
    call_command("open_next_period", verbosity=0)
    assert TimePeriod.objects.filter(company=company).count() == 2


@pytest.mark.django_db
def test_open_next_period_skips_companies_with_no_periods(company):
    call_command("open_next_period", verbosity=0)
    assert TimePeriod.objects.filter(company=company).count() == 0


# ---------------------------------------------------------------------------
# Manual open/close via views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_period_manager_can_close_period(company, period_manager_user):
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 12), status="open")
    client = Client()
    client.force_login(period_manager_user)
    response = client.post(f"/periods/{period.pk}/close/")
    assert response.status_code == 302
    period.refresh_from_db()
    assert period.status == "closed"


@pytest.mark.django_db
def test_period_manager_can_open_period(company, period_manager_user):
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 12), status="closed")
    client = Client()
    client.force_login(period_manager_user)
    response = client.post(f"/periods/{period.pk}/open/")
    assert response.status_code == 302
    period.refresh_from_db()
    assert period.status == "open"


@pytest.mark.django_db
def test_admin_can_manage_periods(company, admin_user):
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 12), status="open")
    client = Client()
    client.force_login(admin_user)
    response = client.post(f"/periods/{period.pk}/close/")
    assert response.status_code == 302
    period.refresh_from_db()
    assert period.status == "closed"


@pytest.mark.django_db
def test_employee_without_period_manager_flag_cannot_manage(company, employee_user):
    period = make_period(company, date(2025, 1, 6), date(2025, 1, 12), status="open")
    client = Client()
    client.force_login(employee_user)
    response = client.get("/periods/")
    assert response.status_code == 302
    response = client.post(f"/periods/{period.pk}/close/")
    assert response.status_code == 302
    period.refresh_from_db()
    assert period.status == "open"  # unchanged


@pytest.mark.django_db
def test_unauthenticated_user_cannot_access_periods():
    client = Client()
    response = client.get("/periods/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
