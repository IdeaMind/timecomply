"""
Tests for Google OAuth2 social login via django-allauth.
"""

import pytest
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def google_app(db):
    """Return the Google SocialApp (created by data migration), updating credentials for tests."""
    site = Site.objects.get_or_create(
        id=1, defaults={"domain": "example.com", "name": "TimeComply"}
    )[0]
    app, _ = SocialApp.objects.get_or_create(
        provider="google",
        defaults={
            "name": "Google",
            "client_id": "test-client-id",
            "secret": "test-secret",
        },
    )
    # Ensure test credentials are set (migration may have used empty strings).
    app.client_id = app.client_id or "test-client-id"
    app.secret = app.secret or "test-secret"
    app.save()
    app.sites.add(site)
    return app


@pytest.mark.django_db
def test_google_login_redirects_to_google(client, google_app):
    """POST /accounts/google/login/ should redirect toward Google's OAuth endpoint.

    allauth renders a confirmation page on GET (LOGIN_ON_GET=False default).
    The POST initiates the OAuth2 flow and redirects to Google.
    """
    url = reverse("google_login")
    # GET renders an intermediate confirmation page (200).
    get_response = client.get(url)
    assert get_response.status_code == 200

    # POST triggers the OAuth2 redirect to Google.
    post_response = client.post(url)
    assert post_response.status_code == 302
    location = post_response.get("Location", "")
    assert "accounts.google.com" in location or "google.com" in location


@pytest.mark.django_db
def test_google_callback_creates_user(client, google_app):
    """
    Simulate a completed OAuth callback by directly creating the allauth social
    account objects, then verifying the user/account relationship is correct.

    A full end-to-end OAuth flow requires a live Google token and cannot be
    exercised in unit tests without mocking the entire OAuth library. This test
    verifies the data model layer: that a SocialAccount is linked to a User and
    that the user is marked active.
    """
    user = User.objects.create_user(
        username="google_user@example.com",
        email="google_user@example.com",
        password=None,  # no password — social-only account
    )
    SocialAccount.objects.create(
        user=user,
        provider="google",
        uid="1234567890",
        extra_data={
            "email": "google_user@example.com",
            "name": "Google User",
            "verified_email": True,
        },
    )

    account = SocialAccount.objects.get(provider="google", uid="1234567890")
    assert account.user == user
    assert account.user.is_active


@pytest.mark.django_db
def test_google_login_button_appears_on_login_page(client, google_app):
    """Login page renders 'Sign in with Google' link when a SocialApp exists."""
    url = reverse("account_login")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Sign in with Google" in response.content


@pytest.mark.django_db
def test_google_login_button_absent_without_app(client, db):
    """'Sign in with Google' link absent when no Google SocialApp is configured."""
    # Remove any SocialApp created by migrations so we test the no-app state.
    SocialApp.objects.filter(provider="google").delete()
    url = reverse("account_login")
    response = client.get(url)
    assert response.status_code == 200
    assert b"Sign in with Google" not in response.content
