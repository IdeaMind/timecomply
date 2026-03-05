from django.shortcuts import redirect

from .models import CompanyMembership

EXEMPT_PATHS = (
    "/accounts/",
    "/companies/register/",
    "/companies/invite/",
    "/admin/",
    "/health/",
    "/api/",
    "/static/",
)


class CompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        if request.user.is_authenticated:
            try:
                request.company = request.user.membership.company
            except CompanyMembership.DoesNotExist:
                pass

            if request.company is None and not self._is_exempt(request.path):
                return redirect("companies:register")

        return self.get_response(request)

    def _is_exempt(self, path):
        return any(path.startswith(p) for p in EXEMPT_PATHS)
