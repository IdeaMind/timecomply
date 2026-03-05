from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "company",
        "contract_type",
        "is_active",
        "is_billable",
        "created_at",
    )
    list_filter = ("contract_type", "is_active", "is_billable", "company")
    search_fields = ("code", "name", "company__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("company", "code")
