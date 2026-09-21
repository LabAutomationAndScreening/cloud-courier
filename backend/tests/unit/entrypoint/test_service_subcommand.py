# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import sys

import pytest
from backend_api.entrypoint.cli import entrypoint

from .fixtures import restore_logging_levels  # noqa: F401 # autouse fixture imported for side effect


@pytest.mark.skipif(sys.platform == "win32", reason="tests the non-Windows platform guard")
@pytest.mark.parametrize(
    "argv",
    [
        ["service"],
        ["service", "install"],
        ["service", "start"],
        ["service", "stop"],
        ["service", "remove"],
        ["service", "debug"],
    ],
)
def test_Given_service_subcommand_on_non_windows__Then_exit_code_2_with_platform_message(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
):
    platform_guard_exit_code = 2

    exit_code = entrypoint(argv)

    captured = capsys.readouterr()
    assert exit_code == platform_guard_exit_code
    assert "Windows service management" in captured.err.strip()
