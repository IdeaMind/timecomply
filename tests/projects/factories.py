import factory

from apps.projects.models import Project
from tests.companies.factories import CompanyFactory


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    company = factory.SubFactory(CompanyFactory)
    timekeeping_code = factory.Sequence(lambda n: f"P{n:03d}")
    name = factory.Sequence(lambda n: f"Project {n}")
    parent = None
    coa_code = ""
    is_billable = True
    auto_add_to_timesheet = False
    is_archived = False
