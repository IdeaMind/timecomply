import pytest
from django.test import RequestFactory

from apps.companies.middleware import CompanyMiddleware

from .factories import CompanyMembershipFactory, UserFactory


def get_response(request):
    from django.http import HttpResponse

    return HttpResponse("ok")


@pytest.fixture
def middleware():
    return CompanyMiddleware(get_response)


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.mark.django_db
def test_middleware_sets_company(middleware, rf):
    membership = CompanyMembershipFactory()
    user = membership.user
    request = rf.get("/dashboard/")
    request.user = user
    middleware(request)
    assert request.company == membership.company


@pytest.mark.django_db
def test_middleware_none_for_anonymous(middleware, rf):
    from django.contrib.auth.models import AnonymousUser

    request = rf.get("/")
    request.user = AnonymousUser()
    middleware(request)
    assert request.company is None


@pytest.mark.django_db
def test_middleware_none_when_no_membership(middleware, rf):
    user = UserFactory()
    request = rf.get("/companies/register/")
    request.user = user
    middleware(request)
    assert request.company is None


@pytest.mark.django_db
def test_middleware_redirects_authenticated_without_company(rf):
    user = UserFactory()
    request = rf.get("/dashboard/")
    request.user = user
    middleware = CompanyMiddleware(get_response)
    response = middleware(request)
    assert response.status_code == 302
    assert "/companies/register/" in response["Location"]


@pytest.mark.django_db
def test_middleware_does_not_redirect_on_register_path(rf):
    user = UserFactory()
    request = rf.get("/companies/register/")
    request.user = user
    middleware = CompanyMiddleware(get_response)
    response = middleware(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_middleware_does_not_redirect_on_accounts_path(rf):
    user = UserFactory()
    request = rf.get("/accounts/login/")
    request.user = user
    middleware = CompanyMiddleware(get_response)
    response = middleware(request)
    assert response.status_code == 200
