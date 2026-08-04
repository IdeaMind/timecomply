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


# ---------------------------------------------------------------------------
# Bulk assign_employees view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_assign_employees_bulk_creates_relationships(client):
    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    emp1 = _add_employee(company)
    emp2 = _add_employee(company)
    client.force_login(admin)

    response = client.post(
        f"/approvals/setup/supervisor/{approver.pk}/assign/",
        {"employee_ids": [emp1.pk, emp2.pk]},
    )
    assert response.status_code == 302
    assert ApproverRelationship.objects.filter(
        company=company, primary_approver=approver, employee=emp1
    ).exists()
    assert ApproverRelationship.objects.filter(
        company=company, primary_approver=approver, employee=emp2
    ).exists()


@pytest.mark.django_db
def test_assign_employees_reassigns_existing_relationship(client):
    company, admin = _setup_company_with_admin()
    approver1 = _add_approver(company)
    approver2 = _add_approver(company)
    emp = _add_employee(company)

    ApproverRelationship.objects.create(
        employee=emp, company=company, primary_approver=approver1
    )
    client.force_login(admin)

    client.post(
        f"/approvals/setup/supervisor/{approver2.pk}/assign/",
        {"employee_ids": [emp.pk]},
    )
    rel = ApproverRelationship.objects.get(employee=emp, company=company)
    assert rel.primary_approver == approver2


@pytest.mark.django_db
def test_assign_employees_invalid_supervisor_rejected(client):
    company, admin = _setup_company_with_admin()
    emp = _add_employee(company)
    # emp is not an approver, so using their pk as supervisor should fail
    client.force_login(admin)

    response = client.post(
        f"/approvals/setup/supervisor/{emp.pk}/assign/",
        {"employee_ids": [emp.pk]},
    )
    assert response.status_code == 302
    assert not ApproverRelationship.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_assign_employees_non_admin_blocked(client):
    company, _ = _setup_company_with_admin()
    approver = _add_approver(company)
    emp = _add_employee(company)
    client.force_login(emp)

    response = client.post(
        f"/approvals/setup/supervisor/{approver.pk}/assign/",
        {"employee_ids": [emp.pk]},
    )
    assert response.status_code == 302
    assert not ApproverRelationship.objects.filter(company=company).exists()


# ---------------------------------------------------------------------------
# remove_employee view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_remove_employee_deletes_relationship(client):
    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    emp = _add_employee(company)
    rel = ApproverRelationship.objects.create(
        employee=emp, company=company, primary_approver=approver
    )
    client.force_login(admin)

    response = client.post(f"/approvals/setup/relationship/{rel.pk}/remove/")
    assert response.status_code == 302
    assert not ApproverRelationship.objects.filter(pk=rel.pk).exists()


@pytest.mark.django_db
def test_remove_employee_non_admin_blocked(client):
    company, _ = _setup_company_with_admin()
    approver = _add_approver(company)
    emp = _add_employee(company)
    rel = ApproverRelationship.objects.create(
        employee=emp, company=company, primary_approver=approver
    )
    client.force_login(emp)

    client.post(f"/approvals/setup/relationship/{rel.pk}/remove/")
    assert ApproverRelationship.objects.filter(pk=rel.pk).exists()


# ---------------------------------------------------------------------------
# add_backup_rule / remove_backup_rule views
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_add_backup_rule_creates_rule_and_propagates(client):
    from apps.approvals.models import BackupApproverRule

    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    backup = _add_approver(company)
    emp = _add_employee(company)

    # Pre-existing relationship for propagation
    rel = ApproverRelationship.objects.create(
        employee=emp, company=company, primary_approver=approver
    )
    client.force_login(admin)

    response = client.post(
        f"/approvals/setup/supervisor/{approver.pk}/add-rule/",
        {"backup_approver_id": backup.pk},
    )
    assert response.status_code == 302
    assert BackupApproverRule.objects.filter(
        company=company, supervisor=approver, backup_approver=backup
    ).exists()
    # Rule should have propagated to the existing employee relationship
    assert BackupApprover.objects.filter(relationship=rel, approver=backup).exists()


@pytest.mark.django_db
def test_add_backup_rule_duplicate_is_idempotent(client):
    from apps.approvals.models import BackupApproverRule

    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    backup = _add_approver(company)

    BackupApproverRule.objects.create(
        company=company, supervisor=approver, backup_approver=backup
    )
    client.force_login(admin)

    client.post(
        f"/approvals/setup/supervisor/{approver.pk}/add-rule/",
        {"backup_approver_id": backup.pk},
    )
    # Should still only be one rule
    assert (
        BackupApproverRule.objects.filter(
            company=company, supervisor=approver, backup_approver=backup
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_add_backup_rule_non_approver_rejected(client):
    from apps.approvals.models import BackupApproverRule

    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    emp = _add_employee(company)  # not an approver
    client.force_login(admin)

    client.post(
        f"/approvals/setup/supervisor/{approver.pk}/add-rule/",
        {"backup_approver_id": emp.pk},
    )
    assert not BackupApproverRule.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_remove_backup_rule_deletes_rule_and_backups(client):
    from apps.approvals.models import BackupApproverRule

    company, admin = _setup_company_with_admin()
    approver = _add_approver(company)
    backup = _add_approver(company)
    emp = _add_employee(company)

    rule = BackupApproverRule.objects.create(
        company=company, supervisor=approver, backup_approver=backup
    )
    rel = ApproverRelationship.objects.create(
        employee=emp, company=company, primary_approver=approver
    )
    BackupApprover.objects.create(relationship=rel, approver=backup, source_rule=rule)
    client.force_login(admin)

    response = client.post(f"/approvals/setup/rule/{rule.pk}/remove/")
    assert response.status_code == 302
    assert not BackupApproverRule.objects.filter(pk=rule.pk).exists()
    # Cascade: BackupApprover records created from this rule should be deleted
    assert not BackupApprover.objects.filter(relationship=rel, approver=backup).exists()
