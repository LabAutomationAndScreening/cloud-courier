# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import random
import tempfile
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import ANY
from uuid import uuid4

import pytest
import uvicorn
from backend_api import app_runner
from backend_api.entrypoint.cli import entrypoint
from backend_api.jinja_constants import APP_NAME
from backend_api.jinja_constants import DEFAULT_DEPLOYED_HOST
from backend_api.jinja_constants import DEPLOYED_PORT_NUMBER
from pytest_mock import MockerFixture

from .fixtures import GENERIC_REQUIRED_CLI_ARGS
from .fixtures import random_non_info_log_level
from .fixtures import restore_logging_levels  # noqa: F401 # autouse fixture imported for side effect
from .fixtures import restore_signal_handlers  # noqa: F401 # autouse fixture imported for side effect


class TestCliArgParsing:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        self.mocker = mocker
        self.mocked_run = mocker.patch.object(uvicorn.Server, uvicorn.Server.run.__name__, autospec=True)
        self.spied_server_init = mocker.spy(uvicorn.Server, uvicorn.Server.__init__.__name__)

    def _spy_on_configure_logging(self):
        self.spied_configure_logging = self.mocker.spy(app_runner, app_runner.configure_logging.__name__)

    def _built_config(self) -> uvicorn.Config:
        built_config = self.spied_server_init.call_args.args[1]
        assert isinstance(built_config, uvicorn.Config)
        return built_config

    def _run_entrypoint(self, argv: Sequence[str]) -> None:
        self.exit_code = entrypoint(argv)
        if self.exit_code != 0:
            raise AssertionError(f"entrypoint returned non-zero exit code {self.exit_code}; argv={argv}")

    def test_Given_log_level_specified__Then_app_log_level_passed_to_configure_logging(self):
        expected_log_level = random_non_info_log_level()
        self._spy_on_configure_logging()

        self._run_entrypoint([f"--log-level={expected_log_level}"])

        self.spied_configure_logging.assert_called_once_with(
            log_level=expected_log_level,
            log_filename_prefix=ANY,
            suppress_console_logging=ANY,  # specific to this repository, covered by its own test
        )

    def test_Given_log_folder_specified__Then_log_folder_passed_to_configure_logging(self):
        self._spy_on_configure_logging()
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_log_folder = temp_dir

            self._run_entrypoint([f"--log-folder={expected_log_folder}"])

        self.spied_configure_logging.assert_called_once_with(
            log_filename_prefix=str(Path(expected_log_folder) / f"{APP_NAME}-"),
            log_level=ANY,
            suppress_console_logging=ANY,  # specific to this repository, covered by its own test
        )

    def test_Given_log_level_specified__Then_log_level_passed_to_uvicorn(self):
        expected_log_level = random_non_info_log_level()

        self._run_entrypoint([f"--log-level={expected_log_level}"])

        assert self._built_config().log_level == expected_log_level.lower()

    def test_Given_port_specified__Then_port_passed_to_uvicorn(self):
        expected_port = random.randint(1000, 9999)

        self._run_entrypoint([f"--port={expected_port}"])

        assert self._built_config().port == expected_port

    def test_Given_host_specified__Then_host_passed_to_uvicorn(self):
        expected_host = str(uuid4())

        self._run_entrypoint([f"--host={expected_host}"])

        assert self._built_config().host == expected_host

    def test_Given_no_args__Then_default_port_and_host_used(self):
        expected_port = DEPLOYED_PORT_NUMBER
        expected_host = DEFAULT_DEPLOYED_HOST

        self._run_entrypoint(GENERIC_REQUIRED_CLI_ARGS)

        config = self._built_config()

        assert config.host == expected_host
        assert config.port == expected_port

    def test_Given_no_args__Then_default_log_config_used_for_app(self):
        self._spy_on_configure_logging()

        self._run_entrypoint(GENERIC_REQUIRED_CLI_ARGS)

        self.spied_configure_logging.assert_called_once_with(
            log_filename_prefix=str(Path("logs") / f"{APP_NAME}-"),
            log_level="INFO",
            suppress_console_logging=False,  # specific to this repository: the default when --no-console-logging is absent
        )

    def test_Given_no_args__Then_default_log_config_used_for_uvicorn(self):
        self._run_entrypoint(GENERIC_REQUIRED_CLI_ARGS)

        assert self._built_config().log_level == "info"

    def test_Given_entrypoint_invoked__Then_uvicorn_server_run_invoked(self):
        self._run_entrypoint(GENERIC_REQUIRED_CLI_ARGS)

        self.mocked_run.assert_called_once()
