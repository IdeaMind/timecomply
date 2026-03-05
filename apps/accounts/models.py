from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )
    timezone = models.CharField(max_length=64, default="America/New_York")
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Profile for {self.user}"
