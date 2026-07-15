# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-python-package-template
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import logging

import pytest

logger = logging.getLogger(__name__)


def pytest_configure(
    config: pytest.Config,
):
    """Configure pytest itself, such as logging levels."""
