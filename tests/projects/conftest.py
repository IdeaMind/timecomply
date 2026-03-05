"""
Fixtures for the projects test suite.

The signal that seeds the default labor category tree on Company creation is
disconnected here so that individual tests can set up their own data without
conflicting with the default tree codes (1, 2, 2.1, etc.).
"""

import pytest
from django.db.models.signals import post_save

from apps.projects.signals import seed_default_labor_categories


@pytest.fixture(autouse=True)
def disable_seed_signal():
    """Disconnect the labor category seed signal for all project tests."""
    post_save.disconnect(seed_default_labor_categories, sender="companies.Company")
    yield
    post_save.connect(seed_default_labor_categories, sender="companies.Company")
