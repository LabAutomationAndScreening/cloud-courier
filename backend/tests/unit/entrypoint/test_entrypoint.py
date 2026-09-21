# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from random import randint
from uuid import uuid4

import pytest
from backend_api import app_runner
from backend_api.entrypoint import cli
from backend_api.entrypoint import grant_rights
from backend_api.entrypoint.cli import entrypoint
from pytest_mock import MockerFixture

from .fixtures import GENERIC_REQUIRED_CLI_ARGS
from .fixtures import restore_logging_levels  # noqa: F401 # autouse fixture imported for side effect
from .fixtures import restore_signal_handlers  # noqa: F401 # autouse fixture imported for side effect


def test_Given_invalid_cli_args__Then_exit_code_is_2():
    # TODO: capture the log message so the stderr is not overrun with log messages during testing
    invalid_args = ["--invalid-arg"]
    argparse_exit_code = 2

    exit_code = entrypoint(invalid_args)

    assert exit_code == argparse_exit_code


def test_When_version__Then_returns_something_looking_like_semver(capsys: pytest.CaptureFixture[str]):
    expected_num_dots_in_version = 2

    with pytest.raises(SystemExit) as e:  # noqa: PT011 # there is nothing meaningful to match against for the text of this error, we are asserting later that the exit code is zero
        _ = entrypoint(["--version"])
    assert e.value.code == 0

    captured = capsys.readouterr()
    actual_version = captured.out.strip()

    assert actual_version.startswith("v")
    assert actual_version.count(".") == expected_num_dots_in_version


def test_Given_something_mocked_to_error__Then_error_logged(mocker: MockerFixture):
    expected_error = str(uuid4())
    spied_logger = mocker.spy(cli.logger, "exception")
    _ = mocker.patch.object(
        app_runner,
        app_runner.app_specific_setup.__name__,
        autospec=True,
        side_effect=RuntimeError(expected_error),
    )

    with pytest.raises(RuntimeError, match=expected_error):
        _ = entrypoint(GENERIC_REQUIRED_CLI_ARGS)

    spied_logger.assert_called_once()


def test_Given_launched_directly_via_uvicorn__Then_return_zero():
    exit_code = entrypoint(["src.entrypoint:app"])

    assert exit_code == 0


def test_Given_grant_service_rights_subcommand__Then_remaining_argv_forwarded_unparsed(mocker: MockerFixture):
    expected_exit_code = randint(1, 255)
    # Opaque tokens (not real flags) prove the entrypoint forwards whatever follows
    # the subcommand verbatim to the dispatcher, so new grant-service-rights flags
    # ride along without a change here. Flag parsing is covered in test_grant_rights.
    remaining_argv = [str(uuid4()), str(uuid4())]
    dispatch_mock = mocker.patch.object(
        grant_rights, grant_rights.dispatch_grant_rights.__name__, return_value=expected_exit_code
    )

    exit_code = entrypoint(["grant-service-rights", *remaining_argv])

    assert exit_code == expected_exit_code
    dispatch_mock.assert_called_once_with(remaining_argv)
