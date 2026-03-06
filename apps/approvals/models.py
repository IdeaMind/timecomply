import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.companies.models import CompanyMembership


class ApproverRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approver_relationship",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="approver_relationships",
    )
    primary_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="primary_for",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["employee__username"]

    def __str__(self):
        return f"{self.employee} -> {self.primary_approver} ({self.company})"

    def clean(self):
        if self.employee_id and self.primary_approver_id:
            if self.employee_id == self.primary_approver_id:
                raise ValidationError("An employee cannot be their own approver.")

        if self.primary_approver_id and self.company_id:
            approver_membership = CompanyMembership.objects.filter(
                user_id=self.primary_approver_id, company_id=self.company_id
            ).first()
            if not approver_membership:
                raise ValidationError("Approver must be a member of the same company.")
            if not (approver_membership.is_approver or approver_membership.is_admin):
                raise ValidationError(
                    "Selected user does not have approver permission."
                )


class BackupApprover(models.Model):
    relationship = models.ForeignKey(
        ApproverRelationship,
        on_delete=models.CASCADE,
        related_name="backup_approvers",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backup_approver_for",
    )
    priority = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "approver"], name="unique_backup_approver"
            )
        ]

    def __str__(self):
        emp = self.relationship.employee
        return f"Backup approver {self.approver} (priority {self.priority}) for {emp}"

    def clean(self):
        if self.approver_id and self.relationship_id:
            rel = self.relationship
            if self.approver_id == rel.employee_id:
                raise ValidationError(
                    "An employee cannot be their own backup approver."
                )

            backup_membership = CompanyMembership.objects.filter(
                user_id=self.approver_id, company_id=rel.company_id
            ).first()
            if not backup_membership:
                raise ValidationError(
                    "Backup approver must be a member of the same company."
                )
            if not (backup_membership.is_approver or backup_membership.is_admin):
                raise ValidationError(
                    "Selected backup approver does not have approver permission."
                )


def get_approver_for(employee, company):
    """Return the primary approver, or None if no active relationship exists."""
    try:
        rel = ApproverRelationship.objects.get(
            employee=employee, company=company, is_active=True
        )
        return rel.primary_approver
    except ApproverRelationship.DoesNotExist:
        return None
