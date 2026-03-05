from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from .models import INVITATION_ROLE_CHOICES, Company, CompanyMembership, Invitation

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


@login_required
def members_list(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or membership.role != "admin":
        messages.error(request, "Only company admins can manage members.")
        return redirect("/dashboard/")

    company = membership.company
    members = company.memberships.select_related("user").filter(is_active=True)
    pending_invitations = company.invitations.filter(
        is_revoked=False, accepted_at=None
    ).select_related("invited_by")

    return render(
        request,
        "companies/members.html",
        {
            "company": company,
            "members": members,
            "pending_invitations": [
                inv for inv in pending_invitations if not inv.is_expired()
            ],
        },
    )


@login_required
def invite_member(request):
    membership = getattr(request.user, "membership", None)
    if membership is None or membership.role != "admin":
        messages.error(request, "Only company admins can invite members.")
        return redirect("/dashboard/")

    company = membership.company

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", "")

        if not email:
            messages.error(request, "Email address is required.")
        elif role not in dict(INVITATION_ROLE_CHOICES):
            messages.error(request, "Invalid role selected.")
        else:
            invitation = Invitation.objects.create(
                company=company,
                email=email,
                role=role,
                invited_by=request.user,
            )
            _send_invitation_email(request, invitation)
            messages.success(request, f"Invitation sent to {email}.")
            return redirect("companies:members")

    return render(
        request,
        "companies/invite.html",
        {
            "company": company,
            "role_choices": INVITATION_ROLE_CHOICES,
        },
    )


def accept_invite(request, token):
    invitation = get_object_or_404(Invitation, token=token)

    if not invitation.is_valid():
        if invitation.is_revoked:
            messages.error(request, "This invitation has been revoked.")
        elif invitation.is_expired():
            messages.error(request, "This invitation has expired.")
        else:
            messages.error(request, "This invitation has already been used.")
        return render(request, "companies/invite_invalid.html", status=400)

    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next=/companies/invite/{token}/")

    if hasattr(request.user, "membership"):
        messages.error(request, "You are already a member of a company.")
        return render(request, "companies/invite_invalid.html", status=400)

    CompanyMembership.objects.create(
        user=request.user,
        company=invitation.company,
        role=invitation.role,
        invited_by=invitation.invited_by,
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])

    messages.success(
        request,
        f"Welcome! You have joined {invitation.company.name} as "
        f"{invitation.get_role_display()}.",
    )
    return redirect("/dashboard/")


@login_required
def revoke_invite(request, token):
    membership = getattr(request.user, "membership", None)
    if membership is None or membership.role != "admin":
        messages.error(request, "Only company admins can revoke invitations.")
        return redirect("/dashboard/")

    invitation = get_object_or_404(Invitation, token=token, company=membership.company)

    if request.method == "POST":
        invitation.is_revoked = True
        invitation.save(update_fields=["is_revoked"])
        messages.success(request, f"Invitation to {invitation.email} has been revoked.")
        return redirect("companies:members")

    return redirect("companies:members")


def _send_invitation_email(request, invitation):
    accept_url = request.build_absolute_uri(f"/companies/invite/{invitation.token}/")
    body = render_to_string(
        "email/invitation.txt",
        {
            "invitation": invitation,
            "accept_url": accept_url,
        },
    )
    send_mail(
        subject=f"You've been invited to join {invitation.company.name} on TimeComply",
        message=body,
        from_email=None,
        recipient_list=[invitation.email],
        fail_silently=False,
    )


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
