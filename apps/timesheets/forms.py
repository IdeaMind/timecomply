from django import forms

from .models import TimeEntry


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ["labor_category", "date", "hours", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0", "max": "24"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            from apps.projects.models import Project

            self.fields["labor_category"].queryset = Project.objects.filter(
                company=company, is_archived=False
            ).order_by("timekeeping_code")
        self.fields["labor_category"].label = "Labor Category"
        self.fields["notes"].required = False
