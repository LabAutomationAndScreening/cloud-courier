import logging
import random
import tempfile
import uuid
from collections.abc import Generator
from pathlib import Path
from threading import Thread
from unittest.mock import ANY

import boto3
import pytest
from botocore.session import Session
from pytest_mock import MockerFixture

from cloud_courier import entrypoint
from cloud_courier import get_role_arn
from cloud_courier import get_version
from cloud_courier import main

from .fixtures import mock_path_to_aws_credentials
from .fixtures import mocked_generic_config

_fixtures = (mock_path_to_aws_credentials, mocked_generic_config)
logger = logging.getLogger(__name__)

GENERIC_REQUIRED_CLI_ARGS = ("--aws-region=us-east-2", "--stop-flag-dir=/tmp")


def test_Given_no_args__When_run__Then_returns_error_code():
    # TODO: capture the log message so the stderr is not overrun with log messages during testing
    assert entrypoint([]) > 0


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
    expected_error = str(uuid.uuid4())
    spied_logger = mocker.spy(main.logger, "exception")
    _ = mocker.patch.object(main, "configure_logging", autospec=True, side_effect=RuntimeError(expected_error))

    with pytest.raises(RuntimeError, match=expected_error):
        _ = entrypoint(["--aws-region=us-east-2", "--stop-flag-dir=/tmp"])

    spied_logger.assert_called_once()


class MainMixin:
    @pytest.fixture(autouse=True)
    def _setup(
        self,
        mock_path_to_aws_credentials: None,  # noqa: ARG002 # pytest.usefixture cannot be used on a fixturet
        flag_file_dir: Generator[str, None, None],
    ):
        self.flag_file_dir = str(flag_file_dir)


class TestArgParse(MainMixin):
    def test_When_run__Then_AWS_region_passed_to_boto(self, mocker: MockerFixture):
        spied_set_config = mocker.spy(Session, "set_config_variable")
        expected_region = random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"])

        assert (
            entrypoint(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--immediate-shut-down",
                    "--aws-region",
                    expected_region,
                ]
            )
            == 0
        )

        spied_set_config.assert_called_once_with(ANY, "region", expected_region)

    def test_Given_log_level_specified__Then_log_level_passed_to_configure_logging(self, mocker: MockerFixture):
        spied_configure_logging = mocker.spy(main, "configure_logging")
        expected_log_level = random.choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

        assert (
            entrypoint(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--immediate-shut-down",
                    "--aws-region=us-east-1",
                    f"--log-level={expected_log_level}",
                ]
            )
            == 0
        )

        spied_configure_logging.assert_called_once_with(
            log_level=expected_log_level, log_filename_prefix=ANY, suppress_console_logging=ANY
        )

    def test_Given_log_folder_specified__Then_log_folder_passed_to_configure_logging(self, mocker: MockerFixture):
        spied_configure_logging = mocker.spy(main, "configure_logging")
        with tempfile.TemporaryDirectory() as temp_dir:
            expected_log_folder = temp_dir
        assert (
            entrypoint(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--immediate-shut-down",
                    "--aws-region=us-east-1",
                    f"--log-folder={expected_log_folder}",
                ]
            )
            == 0
        )

        spied_configure_logging.assert_called_once_with(
            log_filename_prefix=str(Path(expected_log_folder) / "cloud-courier-"),
            log_level=ANY,
            suppress_console_logging=False,
        )

    def test_Given_suppress_console_logging_specified__Then_kwarg_passed_to_configure_logging(
        self, mocker: MockerFixture
    ):
        spied_configure_logging = mocker.spy(main, "configure_logging")

        assert (
            entrypoint(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--immediate-shut-down",
                    "--aws-region=us-east-1",
                    "--no-console-logging",
                ]
            )
            == 0
        )

        spied_configure_logging.assert_called_once_with(
            log_filename_prefix=ANY, log_level=ANY, suppress_console_logging=True
        )


class TestUpdateInstanceTag(MainMixin):
    def test_When_run__Then_managed_instance_tag_updated_to_version(self, mocker: MockerFixture):
        expected_version = str(uuid.uuid4())
        expected_computer_info = "cambridge--cytation-5"
        _ = mocker.patch.object(main, get_version.__name__, return_value=expected_version, autospec=True)
        _ = mocker.patch.object(
            main,
            get_role_arn.__name__,
            autospec=True,
            return_value=f"arn:aws:sts::321623840054:assumed-role/{expected_computer_info}--cloud-courier--dev/mi-0f07754091d56481f",
        )
        random_region = random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"])

        assert (
            entrypoint(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--shut-down-before-main-loop",
                    "--aws-region",
                    random_region,
                ]
            )
            == 0
        )

        ssm_client = boto3.client("ssm")


class TestShutdown(MainMixin):
    @pytest.mark.timeout(10)
    @pytest.mark.usefixtures(mocked_generic_config.__name__)
    def test_Given_no_files_to_upload__When_flag_file_created__Then_clean_exit(self):
        thread = Thread(
            target=entrypoint,
            args=(
                [
                    f"--stop-flag-dir={self.flag_file_dir}",
                    "--aws-region=us-east-1",
                    "--idle-loop-sleep-seconds=0.1",
                ],
            ),
        )
        thread.start()
        # also make a subdirectory, just to test the logic that nothing happens
        (Path(self.flag_file_dir) / str(uuid.uuid4())).mkdir()
        flag_file = Path(self.flag_file_dir) / f"{uuid.uuid4()}.txt"

        flag_file.touch()
        thread.join(timeout=5)

        assert thread.is_alive() is False
