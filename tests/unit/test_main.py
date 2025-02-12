import logging
import random
import uuid
from collections.abc import Generator
from pathlib import Path
from threading import Thread
from unittest.mock import ANY

import pytest
from botocore.session import Session
from pytest_mock import MockerFixture

from cloud_courier import main

from .fixtures import mock_path_to_aws_credentials

_fixtures = (mock_path_to_aws_credentials,)
logger = logging.getLogger(__name__)


def test_Given_no_args__When_run__Then_returns_error_code():
    # TODO: capture the log message so the stderr is not overrun with log messages during testing
    assert main([]) > 0


# def test_Given_something_mocked_to_error__Then_error_logged(mocker: MockerFixture):
#     spied_logger = mocker.spy(cloud_courier.main.logger, "exception")
#     mocker.patch("cloud_courier.aws_credentials.read_aws_creds", side_effect=Exception("This is a test exception"))

#     assert main([]) > 0

#     spied_logger.assert_called_once_with(ANY, exc_info=ANY)


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
            main([f"--stop-flag-dir={self.flag_file_dir}", "--immediate-shut-down", "--aws-region", expected_region])
            == 0
        )

        spied_set_config.assert_called_once_with(ANY, "region", expected_region)


class TestShutdown(MainMixin):
    @pytest.mark.timeout(10)
    def test_Given_no_files_to_upload__When_flag_file_created__Then_clean_exit(self):
        thread = Thread(
            target=main,
            args=(
                [f"--stop-flag-dir={self.flag_file_dir}", "--aws-region=us-east-1", "--idle-loop-sleep-seconds=0.1"],
            ),
        )
        thread.start()
        # also make a subdirectory, just to test the logic that nothing happens
        (Path(self.flag_file_dir) / str(uuid.uuid4())).mkdir()
        flag_file = Path(self.flag_file_dir) / f"{uuid.uuid4()}.txt"

        flag_file.touch()
        thread.join(timeout=5)

        assert thread.is_alive() is False
