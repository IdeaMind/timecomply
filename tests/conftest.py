"""
Global pytest fixtures for the timecomply test suite.
"""

import pytest


@pytest.fixture
def api_client():
    """Return a DRF API test client."""
    from rest_framework.test import APIClient

    return APIClient()
