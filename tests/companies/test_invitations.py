from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.companies.models import CompanyMembership, Invitation

from .factories import CompanyMembershipFactory, InvitationFactory, UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_membership():
    return CompanyMembershipFactory(role="admin")


# --- Invitation creation ---


@pytest.mark.django_db
def test_admin_can_create_invitation(client, admin_membership):
    client.force_login(admin_membership.user)
    response = client.post(
        "/companies/members/invite/",
        {"email": "newuser@example.com", "role": "employee"},
    )
    assert response.status_code == 302
    assert Invitation.objects.filter(email="newuser@example.com").exists()


@pytest.mark.django_db
def test_invitation_email_sent(client, admin_membership):
    client.force_login(admin_membership.user)
    client.post(
        "/companies/members/invite/",
        {"email": "invited@example.com", "role": "employee"},
    )
    assert len(mail.outbox) == 1
    assert "invited@example.com" in mail.outbox[0].to
    assert admin_membership.company.name in mail.outbox[0].subject


@pytest.mark.django_db
def test_non_admin_cannot_access_invite_view(client):
    membership = CompanyMembershipFactory(role="employee")
    client.force_login(membership.user)
    response = client.get("/companies/members/invite/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"


@pytest.mark.django_db
def test_invite_view_requires_login(client):
    response = client.get("/companies/members/invite/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


# --- Token expiry and revocation ---


@pytest.mark.django_db
def test_expired_invitation_rejected(client):
    invitation = InvitationFactory()
    invitation.created_at = timezone.now() - timedelta(days=8)
    invitation.save(update_fields=["created_at"])

    user = UserFactory()
    client.force_login(user)
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_revoked_invitation_rejected(client):
    invitation = InvitationFactory(is_revoked=True)
    user = UserFactory()
    client.force_login(user)
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_already_accepted_invitation_rejected(client):
    invitation = InvitationFactory(accepted_at=timezone.now())
    user = UserFactory()
    client.force_login(user)
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 400


# --- Accept flow ---


@pytest.mark.django_db
def test_accepting_invitation_creates_membership(client):
    invitation = InvitationFactory(role="employee")
    user = UserFactory()
    client.force_login(user)
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"

    membership = CompanyMembership.objects.get(user=user)
    assert membership.company == invitation.company
    assert membership.role == "employee"

    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


@pytest.mark.django_db
def test_unauthenticated_user_redirected_to_login(client):
    invitation = InvitationFactory()
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
    assert str(invitation.token) in response["Location"]


@pytest.mark.django_db
def test_already_member_cannot_accept_second_invite(client):
    invitation = InvitationFactory()
    existing_membership = CompanyMembershipFactory(role="employee")
    client.force_login(existing_membership.user)
    response = client.get(f"/companies/invite/{invitation.token}/")
    assert response.status_code == 400
    assert CompanyMembership.objects.filter(user=existing_membership.user).count() == 1


# --- Revocation ---


@pytest.mark.django_db
def test_admin_can_revoke_invitation(client, admin_membership):
    invitation = InvitationFactory(company=admin_membership.company)
    client.force_login(admin_membership.user)
    response = client.post(f"/companies/invite/{invitation.token}/revoke/")
    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.is_revoked is True


@pytest.mark.django_db
def test_non_admin_cannot_revoke_invitation(client):
    membership = CompanyMembershipFactory(role="employee")
    invitation = InvitationFactory(company=membership.company)
    client.force_login(membership.user)
    response = client.post(f"/companies/invite/{invitation.token}/revoke/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"
    invitation.refresh_from_db()
    assert invitation.is_revoked is False


# --- Members list ---


@pytest.mark.django_db
def test_admin_can_view_members_list(client, admin_membership):
    client.force_login(admin_membership.user)
    response = client.get("/companies/members/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_view_members_list(client):
    membership = CompanyMembershipFactory(role="employee")
    client.force_login(membership.user)
    response = client.get("/companies/members/")
    assert response.status_code == 302
    assert response["Location"] == "/dashboard/"


# --- Invitation model helpers ---


@pytest.mark.django_db
def test_is_expired_returns_true_after_7_days():
    invitation = InvitationFactory()
    invitation.created_at = timezone.now() - timedelta(days=8)
    invitation.save(update_fields=["created_at"])
    assert invitation.is_expired() is True


@pytest.mark.django_db
def test_is_expired_returns_false_before_7_days():
    invitation = InvitationFactory()
    assert invitation.is_expired() is False


@pytest.mark.django_db
def test_is_valid_false_when_revoked():
    invitation = InvitationFactory(is_revoked=True)
    assert invitation.is_valid() is False


@pytest.mark.django_db
def test_is_valid_false_when_accepted():
    invitation = InvitationFactory(accepted_at=timezone.now())
    assert invitation.is_valid() is False


@pytest.mark.django_db
def test_is_valid_true_for_fresh_invitation():
    invitation = InvitationFactory()
    assert invitation.is_valid() is True
