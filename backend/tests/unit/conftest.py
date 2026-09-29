# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import logging

import pytest
from backend_api import configure_logging
from backend_api.app_def import app
from fastapi import FastAPI

from .snapshot import snapshot_json  # noqa: F401 # this is a fixture we need in conftest scope

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="session")
def configure_log():
    configure_logging(log_filename_prefix="logs/pytest-")


def _get_all_state_attributes(app: FastAPI) -> set[str]:
    return set(
        app.state._state.keys()  # noqa: SLF001 # yes this isn't great, but not sure of another way to be able to keep the state from bleeding over between tests. given the implementation it seems unlikely that _state would change in future versions
    )


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset app state between tests by removing dynamically added attributes."""
    original_attrs = _get_all_state_attributes(app)

    yield

    current_attrs = _get_all_state_attributes(app)
    added_attrs = current_attrs - original_attrs
    for attr in added_attrs:
        delattr(app.state, attr)
