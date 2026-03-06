from django.contrib import admin

from .models import TimeEntry, TimePeriod, Timesheet


@admin.register(TimePeriod)
class TimePeriodAdmin(admin.ModelAdmin):
    list_display = ["company", "start_date", "end_date", "status"]
    list_filter = ["status", "company"]
    search_fields = ["company__name"]
    ordering = ["-start_date"]


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0
    fields = ["labor_category", "date", "hours", "notes", "is_correction"]
    readonly_fields = ["created_at"]


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ["employee", "company", "period", "status", "submitted_at"]
    list_filter = ["status", "company"]
    search_fields = ["employee__username", "employee__email", "company__name"]
    ordering = ["-created_at"]
    inlines = [TimeEntryInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["timesheet", "labor_category", "date", "hours", "is_correction"]
    list_filter = ["is_correction", "timesheet__company"]
    search_fields = ["timesheet__employee__username", "labor_category__name"]
    ordering = ["-date"]
    readonly_fields = ["created_at"]
