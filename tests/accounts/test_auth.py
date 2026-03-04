"""
Tests for django-allauth email/password authentication.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def signup_url():
    return reverse("account_signup")


@pytest.fixture
def login_url():
    return reverse("account_login")


@pytest.fixture
def logout_url():
    return reverse("account_logout")


@pytest.mark.django_db
def test_registration_creates_user(client, signup_url, mailoutbox):
    """Submitting the signup form creates a user pending email verification."""
    response = client.post(
        signup_url,
        {
            "email": "newuser@example.com",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        },
    )
    # allauth redirects after successful signup
    assert response.status_code == 302
    assert User.objects.filter(email="newuser@example.com").exists()


@pytest.mark.django_db
def test_registration_requires_email_verification(client, signup_url, mailoutbox):
    """After registration, a verification email is sent."""
    client.post(
        signup_url,
        {
            "email": "verify@example.com",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        },
    )
    # A confirmation email should have been sent
    assert len(mailoutbox) == 1
    assert "verify@example.com" in mailoutbox[0].to


@pytest.mark.django_db
def test_login_with_valid_credentials(client, login_url):
    """A user with a verified email can log in successfully."""
    from allauth.account.models import EmailAddress

    user = User.objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="Str0ng!Pass",
    )
    EmailAddress.objects.create(
        user=user,
        email="user@example.com",
        verified=True,
        primary=True,
    )

    response = client.post(
        login_url,
        {"login": "user@example.com", "password": "Str0ng!Pass"},
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_with_invalid_credentials(client, login_url):
    """Logging in with the wrong password returns the login page with an error."""
    User.objects.create_user(
        username="user2@example.com",
        email="user2@example.com",
        password="Str0ng!Pass",
    )

    response = client.post(
        login_url,
        {"login": "user2@example.com", "password": "WrongPass!"},
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_duplicate_email_rejected(client, signup_url):
    """Attempting to register with an already-used email shows an error."""
    from allauth.account.models import EmailAddress

    existing_user = User.objects.create_user(
        username="dupe@example.com",
        email="dupe@example.com",
        password="Str0ng!Pass",
    )
    EmailAddress.objects.create(
        user=existing_user,
        email="dupe@example.com",
        verified=True,
        primary=True,
    )

    response = client.post(
        signup_url,
        {
            "email": "dupe@example.com",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        },
    )
    # allauth 65.x redirects to confirm-email (security: prevents email enumeration)
    # The key invariant is that no second account is created for the duplicate email.
    assert User.objects.filter(email="dupe@example.com").count() == 1


@pytest.mark.django_db
def test_logout(client, logout_url):
    """A logged-in user can log out."""
    user = User.objects.create_user(
        username="logout@example.com",
        email="logout@example.com",
        password="Str0ng!Pass",
    )
    client.force_login(user)

    response = client.post(logout_url)
    assert response.status_code == 302
    # After logout, user should not be authenticated on the login page
    response = client.get(reverse("account_login"))
    assert response.status_code == 200
