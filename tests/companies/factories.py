import factory
from django.contrib.auth import get_user_model

from apps.companies.models import Company, CompanyMembership

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Company {n}")
    slug = factory.Sequence(lambda n: f"company-{n}")
    is_active = True
    settings = factory.LazyAttribute(lambda _: {})


class CompanyMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyMembership

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    role = "employee"
    is_period_manager = False
    is_active = True
