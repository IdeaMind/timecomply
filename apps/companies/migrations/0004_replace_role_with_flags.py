from django.db import migrations, models


def role_to_flags(apps, schema_editor):
    CompanyMembership = apps.get_model("companies", "CompanyMembership")
    for membership in CompanyMembership.objects.all():
        membership.is_employee = membership.role == "employee"
        membership.is_approver = membership.role == "approver"
        membership.is_admin = membership.role == "admin"
        membership.save(update_fields=["is_employee", "is_approver", "is_admin"])


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0003_remove_role_from_invitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="companymembership",
            name="is_employee",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="companymembership",
            name="is_approver",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="companymembership",
            name="is_admin",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(role_to_flags, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="companymembership",
            name="role",
        ),
    ]
