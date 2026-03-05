import uuid

from django.db import models


class Project(models.Model):
    """
    Represents a node in the labor category tree.

    Both organizational categories (e.g. 'Direct Labor') and specific
    billable charge codes are nodes in this tree. Leaf nodes are the
    charge codes employees select when entering time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    timekeeping_code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    coa_code = models.CharField(max_length=50, blank=True, default="")
    is_billable = models.BooleanField(default=True)
    auto_add_to_timesheet = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "timekeeping_code"],
                name="unique_project_timekeeping_code_per_company",
            )
        ]

    def __str__(self):
        return f"{self.timekeeping_code} — {self.name}"
