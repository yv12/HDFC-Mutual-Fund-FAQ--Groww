"""
Global Pytest fixtures and safeguards.
"""

import pytest
from app.config import settings


@pytest.fixture(autouse=True, scope="session")
def protect_production_database():
    """
    SAFETY LOCK: Ensure tests can NEVER touch the production Qdrant Cloud collection.
    Automatically overrides Qdrant collection name to an isolated test collection.
    """
    settings.qdrant_collection_name = "test_mutual_fund_faq"
