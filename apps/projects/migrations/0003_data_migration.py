"""
Data migration:
1. Populate is_archived from is_active (invert the boolean).
2. Seed the default labor category tree for each existing company.
3. Map existing projects to appropriate parent nodes based on their contract_type.
"""

from django.db import migrations

DEFAULT_TREE = [
    {
        "timekeeping_code": "1",
        "name": "Direct Labor",
        "is_billable": True,
        "auto_add_to_timesheet": False,
        "children": [],
    },
    {
        "timekeeping_code": "2",
        "name": "Indirect Labor",
        "is_billable": False,
        "auto_add_to_timesheet": False,
        "children": [
            {
                "timekeeping_code": "2.1",
                "name": "Fringe",
                "is_billable": False,
                "auto_add_to_timesheet": False,
                "children": [
                    {
                        "timekeeping_code": "2.1.1",
                        "name": "Holiday",
                        "is_billable": False,
                        "auto_add_to_timesheet": True,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.1.2",
                        "name": "Vacation",
                        "is_billable": False,
                        "auto_add_to_timesheet": True,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.1.3",
                        "name": "Sick Leave / Jury Duty",
                        "is_billable": False,
                        "auto_add_to_timesheet": True,
                        "children": [],
                    },
                ],
            },
            {
                "timekeeping_code": "2.2",
                "name": "Overhead",
                "is_billable": False,
                "auto_add_to_timesheet": False,
                "children": [
                    {
                        "timekeeping_code": "2.2.1",
                        "name": "Technical Training",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.2.2",
                        "name": "Internal Lab Maintenance",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.2.3",
                        "name": "Supervision of Technical Staff",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                ],
            },
            {
                "timekeeping_code": "2.3",
                "name": "G&A",
                "is_billable": False,
                "auto_add_to_timesheet": False,
                "children": [
                    {
                        "timekeeping_code": "2.3.1",
                        "name": "Accounting & Payroll Processing",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.3.2",
                        "name": "Administrative",
                        "is_billable": False,
                        "auto_add_to_timesheet": True,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.3.3",
                        "name": "Training",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.3.4",
                        "name": "B&P (Bid & Proposal)",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                    {
                        "timekeeping_code": "2.3.5",
                        "name": "IR&D (Independent R&D)",
                        "is_billable": False,
                        "auto_add_to_timesheet": False,
                        "children": [],
                    },
                ],
            },
        ],
    },
    {
        "timekeeping_code": "3",
        "name": "Other Labor (Unallowable)",
        "is_billable": False,
        "auto_add_to_timesheet": False,
        "children": [
            {
                "timekeeping_code": "3.1",
                "name": "Internal Morale and Welfare",
                "is_billable": False,
                "auto_add_to_timesheet": False,
                "children": [],
            },
            {
                "timekeeping_code": "3.2",
                "name": "Entertainment Planning",
                "is_billable": False,
                "auto_add_to_timesheet": False,
                "children": [],
            },
        ],
    },
]

# Map old contract_type values to the timekeeping_code of the parent node
CONTRACT_TYPE_TO_PARENT_CODE = {
    "cost_plus": "1",
    "fixed_price": "1",
    "t_m": "1",
    "overhead": "2.2",
    "leave": "2.1",
    "bid_proposal": "2.3",
    "ir_d": "2.3",
}


def migrate_forward(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Company = apps.get_model("companies", "Company")

    # Step 1: Invert is_active into is_archived for all existing projects.
    for project in Project.objects.all():
        project.is_archived = not project.is_active
        project.save(update_fields=["is_archived"])

    # Step 2: For each company, seed the default tree and map existing projects.
    for company in Company.objects.all():
        # Build a map of timekeeping_code → project pk for newly created nodes.
        node_map = {}

        def create_node(node_data, parent_pk=None):
            obj, created = Project.objects.get_or_create(
                company=company,
                timekeeping_code=node_data["timekeeping_code"],
                defaults={
                    "name": node_data["name"],
                    "parent_id": parent_pk,
                    "is_billable": node_data["is_billable"],
                    "auto_add_to_timesheet": node_data["auto_add_to_timesheet"],
                    "is_archived": False,
                },
            )
            node_map[node_data["timekeeping_code"]] = obj.pk
            for child in node_data["children"]:
                create_node(child, parent_pk=obj.pk)

        for node_data in DEFAULT_TREE:
            create_node(node_data)

        # Step 3: Assign parent to existing projects based on their old contract_type.
        existing = Project.objects.filter(company=company).exclude(
            timekeeping_code__in=list(node_map.keys())
        )
        for project in existing:
            parent_code = CONTRACT_TYPE_TO_PARENT_CODE.get(project.contract_type)
            if parent_code and parent_code in node_map:
                project.parent_id = node_map[parent_code]
                project.save(update_fields=["parent_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0002_add_labor_category_fields"),
        ("companies", "0003_remove_role_from_invitation"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrations.RunPython.noop),
    ]
