import pytest
from django.core.exceptions import ValidationError

from apps.approvals.models import ApproverRelationship, BackupApprover, get_approver_for
from tests.companies.factories import (
    CompanyFactory,
    CompanyMembershipFactory,
    UserFactory,
)


def _make_approver_in_company(company):
    """Helper: create a user with is_approver=True in the given company."""
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_approver=True)
    return user


def _make_employee_in_company(company):
    """Helper: create a user with is_employee=True in the given company."""
    user = UserFactory()
    CompanyMembershipFactory(user=user, company=company, is_employee=True)
    return user


@pytest.mark.django_db
def test_self_approval_blocked():
    company = CompanyFactory()
    user = _make_approver_in_company(company)
    # Also make user an employee so we can create an approver relationship
    membership = company.memberships.get(user=user)
    membership.is_employee = True
    membership.save()

    rel = ApproverRelationship(employee=user, company=company, primary_approver=user)
    with pytest.raises(ValidationError, match="cannot be their own approver"):
        rel.full_clean()


@pytest.mark.django_db
def test_cross_company_approver_blocked():
    company1 = CompanyFactory()
    company2 = CompanyFactory()

    employee = _make_employee_in_company(company1)
    # approver is in company2, not company1
    approver = _make_approver_in_company(company2)

    rel = ApproverRelationship(
        employee=employee, company=company1, primary_approver=approver
    )
    with pytest.raises(ValidationError, match="member of the same company"):
        rel.full_clean()


@pytest.mark.django_db
def test_user_without_approver_flag_cannot_be_assigned_as_approver():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    # non_approver has no is_approver or is_admin flag
    non_approver = UserFactory()
    CompanyMembershipFactory(user=non_approver, company=company, is_employee=True)

    rel = ApproverRelationship(
        employee=employee, company=company, primary_approver=non_approver
    )
    with pytest.raises(ValidationError, match="does not have approver permission"):
        rel.full_clean()


@pytest.mark.django_db
def test_admin_can_be_primary_approver():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    admin = UserFactory()
    CompanyMembershipFactory(user=admin, company=company, is_admin=True)

    rel = ApproverRelationship(
        employee=employee, company=company, primary_approver=admin
    )
    rel.full_clean()  # should not raise
    rel.save()
    assert rel.pk is not None


@pytest.mark.django_db
def test_backup_approvers_ordered_by_priority():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    approver = _make_approver_in_company(company)
    backup1 = _make_approver_in_company(company)
    backup2 = _make_approver_in_company(company)
    backup3 = _make_approver_in_company(company)

    CompanyMembershipFactory(
        user=employee, company=company, is_employee=True
    ) if not company.memberships.filter(user=employee).exists() else None

    rel = ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )
    BackupApprover.objects.create(relationship=rel, approver=backup3, priority=3)
    BackupApprover.objects.create(relationship=rel, approver=backup1, priority=1)
    BackupApprover.objects.create(relationship=rel, approver=backup2, priority=2)

    backups = list(rel.backup_approvers.all())
    assert backups[0].approver == backup1
    assert backups[1].approver == backup2
    assert backups[2].approver == backup3


@pytest.mark.django_db
def test_get_approver_returns_primary():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    approver = _make_approver_in_company(company)

    ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )

    result = get_approver_for(employee, company)
    assert result == approver


@pytest.mark.django_db
def test_get_approver_returns_none_when_no_relationship():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)

    result = get_approver_for(employee, company)
    assert result is None


@pytest.mark.django_db
def test_get_approver_returns_none_when_inactive():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    approver = _make_approver_in_company(company)

    ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver, is_active=False
    )

    result = get_approver_for(employee, company)
    assert result is None


@pytest.mark.django_db
def test_unique_backup_approver_constraint():
    company = CompanyFactory()
    employee = _make_employee_in_company(company)
    approver = _make_approver_in_company(company)
    backup = _make_approver_in_company(company)

    rel = ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )
    BackupApprover.objects.create(relationship=rel, approver=backup, priority=1)

    with pytest.raises(Exception):
        BackupApprover.objects.create(relationship=rel, approver=backup, priority=2)


@pytest.mark.django_db
def test_backup_approver_self_approval_blocked():
    company = CompanyFactory()
    employee = UserFactory()
    CompanyMembershipFactory(
        user=employee, company=company, is_employee=True, is_approver=True
    )
    approver = _make_approver_in_company(company)

    rel = ApproverRelationship.objects.create(
        employee=employee, company=company, primary_approver=approver
    )
    backup = BackupApprover(relationship=rel, approver=employee, priority=1)
    with pytest.raises(ValidationError, match="cannot be their own backup approver"):
        backup.full_clean()
