import pytest
from django.test import Client

from apps.approvals.models import ApproverRelationship, BackupApprover
from tests.companies.factories import (
    CompanyFactory,
    CompanyMembershipFactory,
    UserFactory,
)


@pytest.fixture
def client():
    return Client()


def _setup_company_with_admin():
    """Create a company and an admin user."""
    company = CompanyFactory()
    admin_user = UserFactory()
    CompanyMembershipFactory(user=admin_user, company=company, is_admin=True)
    return company, admin_user


def _add_approver(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_approver=True)
    return user


def _add_employee(company):
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    return user


@pytest.mark.django_db
def test_setup_page_requires_login(client):
    response = client.get("/approvals/setup/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_non_admin_cannot_configure_relationships(client):
    company = CompanyFactory()
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    client.force_login(user)
    response = client.get("/approvals/setup/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"


@pytest.mark.django_db
def test_admin_can_configure_relationship(client):
    company, admin = _setup_company_with_admin()
    client.force_login(admin)
    response = client.get("/approvals/setup/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_assign_approver_creates_relationship(client):
    company, admin = _setup_company_with_admin()
    employee = _add_employee(company)
    approver = _add_approver(company)
    client.force_login(admin)

    response = client.post(
        "/approvals/setup/assign/",
        {"employee_id": employee.pk, "primary_approver_id": approver.pk},
    )
    assert response.status_code == 302
    assert ApproverRelationship.objects.filter(
        employee=employee, company=company, primary_approver=approver
    ).exists()


@pytest.mark.django_db
def test_assign_approver_updates_existing_relationship(client):
    company, admin = _setup_company_with_admin()
    employee = _add_employee(company)
    approver1 = _add_approver(company)
    approver2 = _add_approver(company)

    ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver1
    )
    client.force_login(admin)

    client.post(
        "/approvals/setup/assign/",
        {"employee_id": employee.pk, "primary_approver_id": approver2.pk},
    )
    rel = ApproverRelationship.objects.get(employee=employee, company=company)
    assert rel.primary_approver == approver2


@pytest.mark.django_db
def test_assign_self_approver_blocked(client):
    company, admin = _setup_company_with_admin()
    # Make admin also an employee
    membership = company.memberships.get(user=admin)
    membership.is_employee = True
    membership.save()

    client.force_login(admin)
    response = client.post(
        "/approvals/setup/assign/",
        {"employee_id": admin.pk, "primary_approver_id": admin.pk},
    )
    # Should redirect back with an error, not create a relationship
    assert response.status_code == 302
    assert not ApproverRelationship.objects.filter(
        employee=admin, primary_approver=admin
    ).exists()


@pytest.mark.django_db
def test_non_admin_cannot_assign_approver(client):
    company = CompanyFactory()
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    employee = _add_employee(company)
    approver = _add_approver(company)
    client.force_login(user)

    response = client.post(
        "/approvals/setup/assign/",
        {"employee_id": employee.pk, "primary_approver_id": approver.pk},
    )
    assert response.status_code == 302
    assert not ApproverRelationship.objects.exists()


@pytest.mark.django_db
def test_add_backup_approver(client):
    company, admin = _setup_company_with_admin()
    employee = _add_employee(company)
    approver = _add_approver(company)
    backup = _add_approver(company)

    rel = ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )
    client.force_login(admin)

    response = client.post(
        f"/approvals/setup/{rel.pk}/add-backup/",
        {"backup_approver_id": backup.pk, "priority": "2"},
    )
    assert response.status_code == 302
    assert BackupApprover.objects.filter(
        relationship=rel, approver=backup, priority=2
    ).exists()


@pytest.mark.django_db
def test_remove_backup_approver(client):
    company, admin = _setup_company_with_admin()
    employee = _add_employee(company)
    approver = _add_approver(company)
    backup_user = _add_approver(company)

    rel = ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )
    backup = BackupApprover.objects.create(
        relationship=rel, approver=backup_user, priority=1
    )
    client.force_login(admin)

    response = client.post(f"/approvals/setup/backup/{backup.pk}/remove/")
    assert response.status_code == 302
    assert not BackupApprover.objects.filter(pk=backup.pk).exists()
