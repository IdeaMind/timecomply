import factory

from apps.projects.models import Project
from tests.companies.factories import CompanyFactory


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    company = factory.SubFactory(CompanyFactory)
    code = factory.Sequence(lambda n: f"P{n:03d}")
    name = factory.Sequence(lambda n: f"Project {n}")
    contract_type = "cost_plus"
    is_active = True
    is_billable = True
