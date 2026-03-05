import uuid

from django.conf import settings
from django.db import models

COMPANY_SETTINGS_DEFAULTS = {
    "period_type": "weekly",
    "auto_close_hours": None,
    "timezone": "America/New_York",
}


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)
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
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("approver", "Approver"),
        ("employee", "Employee"),
    ]

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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")
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

    def __str__(self):
        return f"{self.user} @ {self.company} ({self.role})"
