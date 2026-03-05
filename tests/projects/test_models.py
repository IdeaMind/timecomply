import pytest
from django.db import IntegrityError

from apps.projects.models import Project
from tests.companies.factories import CompanyFactory


@pytest.mark.django_db
def test_project_str_method():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        timekeeping_code="1",
        name="Direct Labor",
    )
    assert str(project) == "1 — Direct Labor"


@pytest.mark.django_db
def test_project_timekeeping_code_unique_within_company():
    company = CompanyFactory()
    Project.objects.create(
        company=company,
        timekeeping_code="1",
        name="Direct Labor",
    )
    with pytest.raises(IntegrityError):
        Project.objects.create(
            company=company,
            timekeeping_code="1",
            name="Duplicate",
        )


@pytest.mark.django_db
def test_same_timekeeping_code_allowed_in_different_companies():
    company_a = CompanyFactory()
    company_b = CompanyFactory()
    Project.objects.create(
        company=company_a,
        timekeeping_code="1",
        name="Direct Labor A",
    )
    project_b = Project.objects.create(
        company=company_b,
        timekeeping_code="1",
        name="Direct Labor B",
    )
    assert project_b.pk is not None


@pytest.mark.django_db
def test_project_defaults():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        timekeeping_code="1",
        name="Direct Labor",
    )
    assert project.is_archived is False
    assert project.is_billable is True
    assert project.auto_add_to_timesheet is False
    assert project.coa_code == ""
    assert project.parent is None


@pytest.mark.django_db
def test_project_tree_parent_child():
    company = CompanyFactory()
    parent = Project.objects.create(
        company=company,
        timekeeping_code="2",
        name="Indirect Labor",
        is_billable=False,
    )
    child = Project.objects.create(
        company=company,
        timekeeping_code="2.1",
        name="Fringe",
        parent=parent,
        is_billable=False,
    )
    assert child.parent == parent
    assert child in parent.children.all()


@pytest.mark.django_db
def test_project_archive():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        timekeeping_code="1",
        name="Direct Labor",
    )
    assert project.is_archived is False
    project.is_archived = True
    project.save(update_fields=["is_archived"])
    project.refresh_from_db()
    assert project.is_archived is True


@pytest.mark.django_db
def test_project_auto_add_to_timesheet():
    company = CompanyFactory()
    project = Project.objects.create(
        company=company,
        timekeeping_code="2.1.1",
        name="Holiday",
        is_billable=False,
        auto_add_to_timesheet=True,
    )
    assert project.auto_add_to_timesheet is True
