from django.db.models.signals import post_save
from django.dispatch import receiver

DEFAULT_LABOR_CATEGORY_TREE = [
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


def seed_labor_categories_for_company(company):
    """Create the default labor category tree for a company."""
    from .models import Project

    def create_node(node_data, parent=None):
        project, _ = Project.objects.get_or_create(
            company=company,
            timekeeping_code=node_data["timekeeping_code"],
            defaults={
                "name": node_data["name"],
                "parent": parent,
                "is_billable": node_data["is_billable"],
                "auto_add_to_timesheet": node_data["auto_add_to_timesheet"],
            },
        )
        for child in node_data["children"]:
            create_node(child, parent=project)

    for node_data in DEFAULT_LABOR_CATEGORY_TREE:
        create_node(node_data)


@receiver(post_save, sender="companies.Company")
def seed_default_labor_categories(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.projects.exists():
        return
    seed_labor_categories_for_company(instance)
