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
def test_period_manager_flag_independent_of_role():
    user = UserFactory()
    company = CompanyFactory()
    membership = CompanyMembershipFactory(
        user=user,
        company=company,
        role="employee",
        is_period_manager=True,
    )
    assert membership.role == "employee"
    assert membership.is_period_manager is True


@pytest.mark.django_db
def test_membership_default_role_is_employee():
    membership = CompanyMembershipFactory()
    assert membership.role == "employee"


@pytest.mark.django_db
def test_membership_str():
    user = UserFactory(username="alice")
    company = CompanyFactory(name="Acme")
    membership = CompanyMembershipFactory(user=user, company=company, role="admin")
    assert "alice" in str(membership)
    assert "Acme" in str(membership)
    assert "admin" in str(membership)


@pytest.mark.django_db
def test_company_membership_one_to_one_per_user():
    user = UserFactory()
    company1 = CompanyFactory()
    company2 = CompanyFactory()
    CompanyMembershipFactory(user=user, company=company1)
    with pytest.raises(Exception):
        CompanyMembershipFactory(user=user, company=company2)
