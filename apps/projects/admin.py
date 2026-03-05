from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "timekeeping_code",
        "indented_name",
        "company",
        "parent",
        "is_billable",
        "auto_add_to_timesheet",
        "is_archived",
        "created_at",
    )
    list_filter = ("is_archived", "is_billable", "auto_add_to_timesheet", "company")
    search_fields = ("timekeeping_code", "name", "company__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("company", "timekeeping_code")
    raw_id_fields = ("parent",)

    @admin.display(description="Name")
    def indented_name(self, obj):
        depth = 0
        node = obj
        seen = set()
        while node.parent_id and node.parent_id not in seen:
            seen.add(node.pk)
            depth += 1
            node = node.parent
        indent = "\u00a0\u00a0\u00a0\u00a0" * depth
        return f"{indent}{obj.name}"
