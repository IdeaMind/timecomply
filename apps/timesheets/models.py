import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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


class Timesheet(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("locked", "Locked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    period = models.ForeignKey(
        "timesheets.TimePeriod",
        on_delete=models.PROTECT,
        related_name="timesheets",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_timesheets",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["employee", "period"], name="unique_employee_period"
            )
        ]

    def __str__(self):
        return f"{self.employee} | {self.period} | {self.status}"

    @property
    def is_editable(self):
        return self.status == "draft"


class TimeEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    labor_category = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="time_entries",
    )
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)
    is_correction = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "labor_category__timekeeping_code"]

    def __str__(self):
        return (
            f"{self.timesheet.employee} | {self.date}"
            f" | {self.labor_category} | {self.hours}h"
        )

    def clean(self):
        if self.hours is not None and self.hours < 0:
            raise ValidationError("Hours cannot be negative.")
        if self.hours is not None and self.hours > 24:
            raise ValidationError("Hours cannot exceed 24 per entry.")
        if self.timesheet_id and self.date:
            period = self.timesheet.period
            if not (period.start_date <= self.date <= period.end_date):
                raise ValidationError("Date must be within the timesheet period.")
