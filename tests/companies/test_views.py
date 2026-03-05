import pytest
from django.test import Client

from apps.companies.models import Company, CompanyMembership

from .factories import CompanyMembershipFactory, UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_registration_creates_company_with_defaults(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        "/companies/register/",
        {
            "name": "Test Corp",
            "period_type": "biweekly",
            "timezone": "America/Chicago",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"

    company = Company.objects.get(slug="test-corp")
    assert company.name == "Test Corp"
    assert company.settings["period_type"] == "biweekly"
    assert company.settings["timezone"] == "America/Chicago"
    assert company.settings["auto_close_hours"] is None

    membership = CompanyMembership.objects.get(user=user)
    assert membership.company == company
    assert membership.role == "admin"


@pytest.mark.django_db
def test_registration_requires_company_name(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(
        "/companies/register/", {"name": "", "period_type": "weekly"}
    )
    assert response.status_code == 200
    assert Company.objects.count() == 0


@pytest.mark.django_db
def test_registration_page_requires_login(client):
    response = client.get("/companies/register/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_settings_page_admin_only(client):
    membership = CompanyMembershipFactory(role="employee")
    client.force_login(membership.user)
    response = client.get("/companies/settings/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"


@pytest.mark.django_db
def test_settings_page_accessible_by_admin(client):
    membership = CompanyMembershipFactory(role="admin")
    client.force_login(membership.user)
    response = client.get("/companies/settings/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_settings_page_updates_company_settings(client):
    membership = CompanyMembershipFactory(role="admin")
    client.force_login(membership.user)
    response = client.post(
        "/companies/settings/",
        {
            "period_type": "monthly",
            "timezone": "America/Los_Angeles",
            "auto_close_hours": "72",
        },
    )
    assert response.status_code == 302
    membership.company.refresh_from_db()
    assert membership.company.settings["period_type"] == "monthly"
    assert membership.company.settings["auto_close_hours"] == 72


@pytest.mark.django_db
def test_settings_page_requires_login(client):
    response = client.get("/companies/settings/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get("/dashboard/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_dashboard_renders_for_authenticated_user(client):
    membership = CompanyMembershipFactory()
    client.force_login(membership.user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
