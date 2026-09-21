# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import pytest

from ..e2e.conftest import configure_log  # noqa: F401 # this is an autouse fixture
from ..e2e.conftest import vcr_config  # noqa: F401 # this is an autouse fixture


def pytest_configure(config: pytest.Config):
    """Disable coverage reporting for Windows service E2E tests."""
    config.pluginmanager.set_blocked("_cov")
