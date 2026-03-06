import pytest

from apps.companies.models import COMPANY_SETTINGS_DEFAULTS

from .factories import CompanyFactory, CompanyMembershipFactory, UserFactory


@pytest.mark.django_db
def test_company_settings_defaults_applied_on_save():
    company = CompanyFactory(settings={})
    assert company.settings["period_type"] == COMPANY_SETTINGS_DEFAULTS["period_type"]
    assert company.settings["timezone"] == COMPANY_SETTINGS_DEFAULTS["timezone"]
    expected = COMPANY_SETTINGS_DEFAULTS["auto_close_hours"]
    assert company.settings["auto_close_hours"] == expected


@pytest.mark.django_db
def test_company_settings_custom_values_preserved():
    company = CompanyFactory(settings={"period_type": "biweekly"})
    assert company.settings["period_type"] == "biweekly"
    assert company.settings["timezone"] == COMPANY_SETTINGS_DEFAULTS["timezone"]


@pytest.mark.django_db
def test_company_slug_is_unique():
    CompanyFactory(slug="my-company")
    with pytest.raises(Exception):
        CompanyFactory(slug="my-company")


@pytest.mark.django_db
def test_company_str():
    company = CompanyFactory(name="Acme Inc")
    assert str(company) == "Acme Inc"


@pytest.mark.django_db
def test_period_manager_flag_independent_of_other_flags():
    user = UserFactory()
    company = CompanyFactory()
    membership = CompanyMembershipFactory(
        user=user,
        company=company,
        is_employee=True,
        is_period_manager=True,
    )
    assert membership.is_employee is True
    assert membership.is_period_manager is True


@pytest.mark.django_db
def test_membership_default_flags_are_false():
    membership = CompanyMembershipFactory()
    assert membership.is_employee is False
    assert membership.is_approver is False
    assert membership.is_admin is False
    assert membership.is_period_manager is False


@pytest.mark.django_db
def test_membership_str():
    user = UserFactory(username="alice")
    company = CompanyFactory(name="Acme")
    membership = CompanyMembershipFactory(user=user, company=company, is_admin=True)
    assert "alice" in str(membership)
    assert "Acme" in str(membership)
    assert "admin" in str(membership)


@pytest.mark.django_db
def test_can_approve_property():
    approver = CompanyMembershipFactory(is_approver=True)
    admin = CompanyMembershipFactory(is_admin=True)
    employee_only = CompanyMembershipFactory(is_employee=True)
    assert approver.can_approve is True
    assert admin.can_approve is True
    assert employee_only.can_approve is False


@pytest.mark.django_db
def test_company_membership_one_to_one_per_user():
    user = UserFactory()
    company1 = CompanyFactory()
    company2 = CompanyFactory()
    CompanyMembershipFactory(user=user, company=company1)
    with pytest.raises(Exception):
        CompanyMembershipFactory(user=user, company=company2)
