import pytest
from django.test import Client

from tests.companies.factories import CompanyFactory, CompanyMembershipFactory

from .factories import ProjectFactory


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_project_list_requires_login(client):
    response = client.get("/projects/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_project_list_shows_active_projects_to_employees(client):
    membership = CompanyMembershipFactory(role="employee")
    company = membership.company
    active = ProjectFactory(company=company, code="P001", is_active=True)
    ProjectFactory(company=company, code="P002", is_active=False)

    client.force_login(membership.user)
    response = client.get("/projects/")
    assert response.status_code == 200
    assert active.code in response.content.decode()
    assert "P002" not in response.content.decode()


@pytest.mark.django_db
def test_project_list_shows_all_projects_to_admins(client):
    membership = CompanyMembershipFactory(role="admin")
    company = membership.company
    active = ProjectFactory(company=company, code="P001", is_active=True)
    inactive = ProjectFactory(company=company, code="P002", is_active=False)

    client.force_login(membership.user)
    response = client.get("/projects/")
    assert response.status_code == 200
    content = response.content.decode()
    assert active.code in content
    assert inactive.code in content


@pytest.mark.django_db
def test_inactive_project_not_shown_to_employees(client):
    membership = CompanyMembershipFactory(role="employee")
    company = membership.company
    ProjectFactory(company=company, code="HIDDEN", is_active=False)

    client.force_login(membership.user)
    response = client.get("/projects/")
    assert "HIDDEN" not in response.content.decode()


@pytest.mark.django_db
def test_admin_can_create_project(client):
    membership = CompanyMembershipFactory(role="admin")
    company = membership.company

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "code": "P001",
            "name": "Main Contract",
            "contract_type": "cost_plus",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert company.projects.filter(code="P001").exists()


@pytest.mark.django_db
def test_employee_cannot_create_project(client):
    membership = CompanyMembershipFactory(role="employee")

    client.force_login(membership.user)
    response = client.get("/projects/create/")
    assert response.status_code == 302
    assert response["Location"].endswith("/projects/")


@pytest.mark.django_db
def test_create_project_validates_unique_code_within_company(client):
    membership = CompanyMembershipFactory(role="admin")
    company = membership.company
    ProjectFactory(company=company, code="P001")

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "code": "P001",
            "name": "Duplicate",
            "contract_type": "fixed_price",
        },
    )
    assert response.status_code == 200
    assert company.projects.filter(code="P001").count() == 1


@pytest.mark.django_db
def test_create_project_same_code_different_company(client):
    membership_a = CompanyMembershipFactory(role="admin")
    company_b = CompanyFactory()
    ProjectFactory(company=company_b, code="P001")

    client.force_login(membership_a.user)
    response = client.post(
        "/projects/create/",
        {
            "code": "P001",
            "name": "Company A Project",
            "contract_type": "t_m",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert membership_a.company.projects.filter(code="P001").exists()


@pytest.mark.django_db
def test_admin_can_deactivate_project(client):
    membership = CompanyMembershipFactory(role="admin")
    project = ProjectFactory(company=membership.company, is_active=True)

    client.force_login(membership.user)
    response = client.post(f"/projects/{project.pk}/deactivate/")
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.is_active is False


@pytest.mark.django_db
def test_admin_can_edit_project(client):
    membership = CompanyMembershipFactory(role="admin")
    project = ProjectFactory(company=membership.company, code="OLD", name="Old Name")

    client.force_login(membership.user)
    response = client.post(
        f"/projects/{project.pk}/edit/",
        {
            "code": "NEW",
            "name": "New Name",
            "contract_type": "fixed_price",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.code == "NEW"
    assert project.name == "New Name"


@pytest.mark.django_db
def test_project_list_scoped_to_company(client):
    membership = CompanyMembershipFactory(role="employee")
    other_company = CompanyFactory()
    ProjectFactory(company=other_company, code="OTHER")
    ProjectFactory(company=membership.company, code="MINE")

    client.force_login(membership.user)
    response = client.get("/projects/")
    content = response.content.decode()
    assert "MINE" in content
    assert "OTHER" not in content
