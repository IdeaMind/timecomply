from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.text import slugify

from .models import Company, CompanyMembership

PERIOD_TYPE_CHOICES = [
    ("weekly", "Weekly"),
    ("biweekly", "Bi-weekly"),
    ("semimonthly", "Semi-monthly"),
    ("monthly", "Monthly"),
]

TIMEZONE_CHOICES = [
    ("America/New_York", "Eastern"),
    ("America/Chicago", "Central"),
    ("America/Denver", "Mountain"),
    ("America/Los_Angeles", "Pacific"),
    ("America/Anchorage", "Alaska"),
    ("Pacific/Honolulu", "Hawaii"),
    ("UTC", "UTC"),
]


@login_required
def register_company(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        period_type = request.POST.get("period_type", "weekly")
        timezone = request.POST.get("timezone", "America/New_York")

        if not name:
            messages.error(request, "Company name is required.")
            return render(
                request,
                "companies/register.html",
                {
                    "period_type_choices": PERIOD_TYPE_CHOICES,
                    "timezone_choices": TIMEZONE_CHOICES,
                },
            )

        slug = _unique_slug(name)
        company = Company.objects.create(
            name=name,
            slug=slug,
            settings={
                "period_type": period_type,
                "timezone": timezone,
            },
        )
        CompanyMembership.objects.create(
            user=request.user,
            company=company,
            role="admin",
        )
        return redirect("/dashboard/")

    return render(
        request,
        "companies/register.html",
        {
            "period_type_choices": PERIOD_TYPE_CHOICES,
            "timezone_choices": TIMEZONE_CHOICES,
        },
    )


@login_required
def company_settings(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or membership.role != "admin":
        messages.error(request, "Only company admins can access settings.")
        return redirect("/dashboard/")

    company = membership.company

    if request.method == "POST":
        period_type = request.POST.get("period_type", "weekly")
        timezone = request.POST.get("timezone", "America/New_York")
        auto_close_hours_raw = request.POST.get("auto_close_hours", "").strip()

        auto_close_hours = None
        if auto_close_hours_raw:
            try:
                auto_close_hours = int(auto_close_hours_raw)
            except ValueError:
                messages.error(request, "Auto-close hours must be a whole number.")
                return render(
                    request,
                    "companies/settings.html",
                    {
                        "company": company,
                        "period_type_choices": PERIOD_TYPE_CHOICES,
                        "timezone_choices": TIMEZONE_CHOICES,
                    },
                )

        company.settings = {
            **company.settings,
            "period_type": period_type,
            "timezone": timezone,
            "auto_close_hours": auto_close_hours,
        }
        company.save()
        messages.success(request, "Settings updated.")
        return redirect("companies:settings")

    return render(
        request,
        "companies/settings.html",
        {
            "company": company,
            "period_type_choices": PERIOD_TYPE_CHOICES,
            "timezone_choices": TIMEZONE_CHOICES,
        },
    )


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


def _unique_slug(name):
    base = slugify(name)
    if not base:
        base = "company"
    slug = base
    counter = 1
    while Company.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
