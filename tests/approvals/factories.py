import factory

from apps.approvals.models import ApproverRelationship, BackupApprover
from tests.companies.factories import (
    CompanyFactory,
    UserFactory,
)


class ApproverRelationshipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ApproverRelationship

    employee = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    primary_approver = factory.SubFactory(UserFactory)
    is_active = True


class BackupApproverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackupApprover

    relationship = factory.SubFactory(ApproverRelationshipFactory)
    approver = factory.SubFactory(UserFactory)
    priority = 1
