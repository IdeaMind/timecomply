import pytest
from django.db import IntegrityError

from apps.projects.models import Project
from tests.companies.factories import CompanyFactory


@pytest.mark.django_db
def test_project_str_method():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        code="P001",
        name="Main Contract",
        contract_type="cost_plus",
    )
    assert str(project) == "P001 — Main Contract"


@pytest.mark.django_db
def test_project_code_unique_within_company():
    company = CompanyFactory()
    Project.objects.create(
        company=company,
        code="P001",
        name="First Project",
        contract_type="cost_plus",
    )
    with pytest.raises(IntegrityError):
        Project.objects.create(
            company=company,
            code="P001",
            name="Duplicate Project",
            contract_type="fixed_price",
        )


@pytest.mark.django_db
def test_same_code_allowed_in_different_companies():
    company_a = CompanyFactory()
    company_b = CompanyFactory()
    Project.objects.create(
        company=company_a,
        code="P001",
        name="Project A",
        contract_type="cost_plus",
    )
    # Should not raise
    project_b = Project.objects.create(
        company=company_b,
        code="P001",
        name="Project B",
        contract_type="fixed_price",
    )
    assert project_b.pk is not None


@pytest.mark.django_db
def test_project_defaults():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        code="P001",
        name="Test",
        contract_type="overhead",
    )
    assert project.is_active is True
    assert project.is_billable is True


@pytest.mark.django_db
def test_project_contract_type_choices():
    valid_types = [c[0] for c in Project.CONTRACT_TYPE_CHOICES]
    assert "cost_plus" in valid_types
    assert "fixed_price" in valid_types
    assert "t_m" in valid_types
    assert "overhead" in valid_types
    assert "leave" in valid_types
    assert "bid_proposal" in valid_types
    assert "ir_d" in valid_types
