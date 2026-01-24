import logging

import pytest

logger = logging.getLogger(__name__)


def pytest_configure(
    config: pytest.Config,
):
    """Configure pytest itself, such as logging levels."""
