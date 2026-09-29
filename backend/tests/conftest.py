# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import tempfile
from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

# pytest only rewrites asserts in the modules it collects as tests (plus conftest and registered plugins), so
# an assert reached through fixtures.py/helpers.py reports a bare AssertionError with no diff unless its
# module is registered here, so a new top-level test package needs adding to this list. The subpackages are
# named individually rather than registering `tests`, which is already imported by the time this conftest runs
# and would only warn.
pytest.register_assert_rewrite("tests.unit", "tests.e2e")


# Fixtures and hooks specific to this repository
@pytest.fixture(autouse=True)
def localstack_profile(mocker: MockerFixture) -> None:
    mocker.patch.dict(
        "os.environ",
        {
            "AWS_PROFILE": "localstack",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_SESSION_TOKEN": "test",
        },
    )


@pytest.fixture
def flag_file_dir() -> Generator[str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir
