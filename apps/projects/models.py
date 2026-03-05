import uuid

from django.db import models


class Project(models.Model):
    CONTRACT_TYPE_CHOICES = [
        ("cost_plus", "Cost Plus"),
        ("fixed_price", "Fixed Price"),
        ("t_m", "Time & Materials"),
        ("overhead", "Overhead / G&A"),
        ("leave", "Leave (Vacation/Sick/Holiday)"),
        ("bid_proposal", "Bid & Proposal (B&P)"),
        ("ir_d", "IR&D"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_billable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_project_code_per_company",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"
