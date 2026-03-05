# ruff: noqa: E501
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        # Drop old unique constraint on "code"
        migrations.RemoveConstraint(
            model_name="project",
            name="unique_project_code_per_company",
        ),
        # Rename code → timekeeping_code
        migrations.RenameField(
            model_name="project",
            old_name="code",
            new_name="timekeeping_code",
        ),
        # Add new unique constraint on timekeeping_code
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(
                fields=["company", "timekeeping_code"],
                name="unique_project_timekeeping_code_per_company",
            ),
        ),
        # Add parent self-FK
        migrations.AddField(
            model_name="project",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="projects.project",
            ),
        ),
        # Add coa_code
        migrations.AddField(
            model_name="project",
            name="coa_code",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        # Add auto_add_to_timesheet
        migrations.AddField(
            model_name="project",
            name="auto_add_to_timesheet",
            field=models.BooleanField(default=False),
        ),
        # Add is_archived (will be populated from is_active in data migration)
        migrations.AddField(
            model_name="project",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
    ]
