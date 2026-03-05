from django.contrib import admin

from .models import Company, CompanyMembership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_period_manager", "is_active")
    list_filter = ("role", "is_period_manager", "is_active")
    search_fields = ("user__email", "company__name")
    readonly_fields = ("id", "created_at")
