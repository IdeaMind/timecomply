import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

COMPANY_SETTINGS_DEFAULTS = {
    "period_type": "weekly",
    "timezone": "America/New_York",
}


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)
    auto_close_hours = models.PositiveIntegerField(null=True, blank=True)
    auto_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        merged = {**COMPANY_SETTINGS_DEFAULTS, **self.settings}
        self.settings = merged
        super().save(*args, **kwargs)


class CompanyMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    is_employee = models.BooleanField(default=False)
    is_approver = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_period_manager = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def can_approve(self):
        return self.is_approver or self.is_admin

    def __str__(self):
        roles = []
        if self.is_admin:
            roles.append("admin")
        if self.is_approver:
            roles.append("approver")
        if self.is_employee:
            roles.append("employee")
        if self.is_period_manager:
            roles.append("period manager")
        role_str = ", ".join(roles) if roles else "no roles"
        return f"{self.user} @ {self.company} ({role_str})"


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitations_sent",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)

    def is_expired(self):
        return (timezone.now() - self.created_at).days >= 7

    def is_valid(self):
        return (
            not self.is_revoked and not self.is_expired() and self.accepted_at is None
        )

    def __str__(self):
        return f"Invitation for {self.email} to {self.company}"
