from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0003_data_migration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="contract_type",
        ),
        migrations.RemoveField(
            model_name="project",
            name="is_active",
        ),
    ]
