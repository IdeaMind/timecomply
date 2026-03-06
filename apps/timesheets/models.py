import uuid

from django.db import models
from django.db.models import UniqueConstraint


class TimePeriod(models.Model):
    PERIOD_TYPE_CHOICES = [
        ("weekly", "Weekly (Mon-Sun)"),
        ("biweekly", "Bi-Weekly (2 weeks, Mon-Sun)"),
        ("semimonthly", "Semi-Monthly (1st-15th, 16th-EOM)"),
        ("monthly", "Monthly"),
    ]
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="time_periods",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    period_type = models.CharField(max_length=15, choices=PERIOD_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    auto_close_hours = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            UniqueConstraint(
                fields=["company", "start_date"], name="unique_period_start"
            )
        ]

    def __str__(self):
        return f"{self.company} | {self.start_date} – {self.end_date} ({self.status})"
