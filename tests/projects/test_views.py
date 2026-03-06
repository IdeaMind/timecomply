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
def test_project_list_shows_active_not_archived_to_employees(client):
    membership = CompanyMembershipFactory(is_employee=True)
    company = membership.company
    ProjectFactory(company=company, timekeeping_code="HIDDEN", is_archived=True)
    active = ProjectFactory(
        company=company, timekeeping_code="ACTIVE", is_archived=False
    )

    client.force_login(membership.user)
    response = client.get("/projects/")
    assert response.status_code == 200
    content = response.content.decode()
    assert active.timekeeping_code in content
    assert "HIDDEN" not in content


@pytest.mark.django_db
def test_project_list_shows_all_to_admins_with_show_archived(client):
    membership = CompanyMembershipFactory(is_admin=True)
    company = membership.company
    active = ProjectFactory(company=company, timekeeping_code="P001", is_archived=False)
    archived = ProjectFactory(
        company=company, timekeeping_code="P002", is_archived=True
    )

    client.force_login(membership.user)
    response = client.get("/projects/?show_archived=1")
    assert response.status_code == 200
    content = response.content.decode()
    assert active.timekeeping_code in content
    assert archived.timekeeping_code in content


@pytest.mark.django_db
def test_admin_can_create_project(client):
    membership = CompanyMembershipFactory(is_admin=True)
    company = membership.company

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "P001",
            "name": "Main Contract",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert company.projects.filter(timekeeping_code="P001").exists()


@pytest.mark.django_db
def test_create_project_redirects_to_edit_form(client):
    membership = CompanyMembershipFactory(is_admin=True)

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "P001",
            "name": "Main Contract",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert "/edit/" in response["Location"]


@pytest.mark.django_db
def test_employee_cannot_create_project(client):
    membership = CompanyMembershipFactory(is_employee=True)

    client.force_login(membership.user)
    response = client.get("/projects/create/")
    assert response.status_code == 302
    assert response["Location"].endswith("/projects/")


@pytest.mark.django_db
def test_create_project_validates_unique_timekeeping_code(client):
    membership = CompanyMembershipFactory(is_admin=True)
    company = membership.company
    ProjectFactory(company=company, timekeeping_code="P001")

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "P001",
            "name": "Duplicate",
        },
    )
    assert response.status_code == 200
    assert company.projects.filter(timekeeping_code="P001").count() == 1


@pytest.mark.django_db
def test_create_project_same_code_different_company(client):
    membership_a = CompanyMembershipFactory(is_admin=True)
    company_b = CompanyFactory()
    ProjectFactory(company=company_b, timekeeping_code="P001")

    client.force_login(membership_a.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "P001",
            "name": "Company A Project",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert membership_a.company.projects.filter(timekeeping_code="P001").exists()


@pytest.mark.django_db
def test_admin_can_archive_project(client):
    membership = CompanyMembershipFactory(is_admin=True)
    project = ProjectFactory(company=membership.company, is_archived=False)

    client.force_login(membership.user)
    response = client.post(f"/projects/{project.pk}/archive/")
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.is_archived is True


@pytest.mark.django_db
def test_admin_can_unarchive_project(client):
    membership = CompanyMembershipFactory(is_admin=True)
    project = ProjectFactory(company=membership.company, is_archived=True)

    client.force_login(membership.user)
    response = client.post(f"/projects/{project.pk}/unarchive/")
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.is_archived is False


@pytest.mark.django_db
def test_admin_can_edit_project(client):
    membership = CompanyMembershipFactory(is_admin=True)
    project = ProjectFactory(
        company=membership.company, timekeeping_code="OLD", name="Old Name"
    )

    client.force_login(membership.user)
    response = client.post(
        f"/projects/{project.pk}/edit/",
        {
            "timekeeping_code": "NEW",
            "name": "New Name",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.timekeeping_code == "NEW"
    assert project.name == "New Name"


@pytest.mark.django_db
def test_edit_project_redirects_to_project_list(client):
    membership = CompanyMembershipFactory(is_admin=True)
    project = ProjectFactory(company=membership.company, timekeeping_code="OLD")

    client.force_login(membership.user)
    response = client.post(
        f"/projects/{project.pk}/edit/",
        {
            "timekeeping_code": "NEW",
            "name": "New Name",
            "is_billable": "on",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == "/projects/"


@pytest.mark.django_db
def test_project_list_scoped_to_company(client):
    membership = CompanyMembershipFactory(is_employee=True)
    other_company = CompanyFactory()
    ProjectFactory(company=other_company, timekeeping_code="OTHER")
    ProjectFactory(company=membership.company, timekeeping_code="MINE")

    client.force_login(membership.user)
    response = client.get("/projects/")
    content = response.content.decode()
    assert "MINE" in content
    assert "OTHER" not in content


@pytest.mark.django_db
def test_duplicate_name_parent_billable_shows_warning(client):
    membership = CompanyMembershipFactory(is_admin=True)
    company = membership.company
    ProjectFactory(
        company=company,
        timekeeping_code="P001",
        name="My Project",
        parent=None,
        is_billable=True,
    )

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "P002",
            "name": "My Project",
            "is_billable": "on",
        },
        follow=True,
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "duplicate" in content.lower()
    assert company.projects.filter(timekeeping_code="P002").exists()


@pytest.mark.django_db
def test_project_with_parent(client):
    membership = CompanyMembershipFactory(is_admin=True)
    company = membership.company
    parent = ProjectFactory(company=company, timekeeping_code="2", name="Indirect")

    client.force_login(membership.user)
    response = client.post(
        "/projects/create/",
        {
            "timekeeping_code": "2.1",
            "name": "Fringe",
            "parent_id": str(parent.pk),
        },
    )
    assert response.status_code == 302
    child = company.projects.get(timekeeping_code="2.1")
    assert child.parent == parent
