import logging
import random
import threading
import uuid
from collections.abc import Generator
from pathlib import Path
from threading import Thread
from unittest.mock import ANY

import boto3
import pytest
import uvicorn
from backend_api import INSTALLED_AGENT_VERSION_TAG_KEY
from backend_api import app_runner
from backend_api import get_role_arn
from backend_api import get_version
from backend_api import main
from backend_api import start_courier
from backend_api.entrypoint.cli import entrypoint
from backend_api.entrypoint.parser import parser
from backend_api.main import MissingCourierArgumentError
from botocore.session import Session
from botocore.stub import Stubber
from pytest_mock import MockerFixture

from .fixtures import mock_path_to_aws_credentials
from .fixtures import mocked_generic_config

_fixtures = (mock_path_to_aws_credentials, mocked_generic_config)
logger = logging.getLogger(__name__)

GENERIC_REQUIRED_CLI_ARGS = ("--aws-region=us-east-2", "--stop-flag-dir=/tmp")


@pytest.fixture
def patched_uvicorn_run(mocker: MockerFixture) -> None:
    _ = mocker.patch.object(uvicorn.Server, uvicorn.Server.run.__name__, autospec=True)


def test_Given_no_aws_region__When_courier_started__Then_raises():
    cli_args = parser.parse_args(["--stop-flag-dir=/tmp"])

    with pytest.raises(MissingCourierArgumentError, match="--aws-region"):
        _ = start_courier(cli_args, stop_event=threading.Event())


def test_Given_no_stop_flag_dir__When_courier_started__Then_raises():
    cli_args = parser.parse_args(["--aws-region=us-east-2"])

    with pytest.raises(MissingCourierArgumentError, match="--stop-flag-dir"):
        _ = start_courier(cli_args, stop_event=threading.Event())


class MainMixin:
    @pytest.fixture(autouse=True)
    def _setup(
        self,
        mock_path_to_aws_credentials: None,  # noqa: ARG002 # pytest.usefixture cannot be used on a fixturet
        flag_file_dir: Generator[str],
    ):
        self.flag_file_dir = str(flag_file_dir)


class TestArgParse(MainMixin):
    def test_When_run__Then_AWS_region_passed_to_boto(self, mocker: MockerFixture):
        spied_set_config = mocker.spy(Session, "set_config_variable")
        expected_region = random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"])
        cli_args = parser.parse_args(
            [
                f"--stop-flag-dir={self.flag_file_dir}",
                "--immediate-shut-down",
                "--aws-region",
                expected_region,
            ]
        )

        assert start_courier(cli_args, stop_event=threading.Event()) == 0

        spied_set_config.assert_called_once_with(ANY, "region", expected_region)

    def test_Given_generic_boto_session_requested__Then_SSM_credentials_not_used(self, mocker: MockerFixture):
        spied_create_boto_session = mocker.spy(main, main.create_boto_session.__name__)
        cli_args = parser.parse_args(
            [
                f"--stop-flag-dir={self.flag_file_dir}",
                "--immediate-shut-down",
                "--aws-region=us-east-1",
                "--use-generic-boto-session",
            ]
        )

        assert start_courier(cli_args, stop_event=threading.Event()) == 0

        spied_create_boto_session.assert_not_called()

    @pytest.mark.usefixtures(patched_uvicorn_run.__name__)
    def test_Given_suppress_console_logging_specified__Then_kwarg_passed_to_configure_logging(
        self, mocker: MockerFixture
    ):
        spied_configure_logging = mocker.spy(app_runner, "configure_logging")

        assert entrypoint(["--no-console-logging", "--skip-upload-agent"]) == 0

        spied_configure_logging.assert_called_once_with(
            log_filename_prefix=ANY, log_level=ANY, suppress_console_logging=True
        )


class TestUpdateInstanceTag(MainMixin):
    def test_When_run__Then_managed_instance_tag_updated_to_version(self, mocker: MockerFixture):
        expected_version = str(uuid.uuid4())
        expected_computer_info = "cambridge--cytation-5"  # arbitrary
        expected_role_name = f"{expected_computer_info}--cloud-courier--dev"  # arbitrary
        expected_instance_id = "mi-0f07754091d56481f"  # arbitrary
        _ = mocker.patch.object(main, get_version.__name__, return_value=expected_version, autospec=True)
        _ = mocker.patch.object(
            main,
            get_role_arn.__name__,
            autospec=True,
            return_value=f"arn:aws:sts::321623840054:assumed-role/{expected_role_name}/{expected_instance_id}",  # arbitrary account ID and instance ID
        )
        random_region = random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"])
        session = boto3.Session(region_name=random_region)
        ssm_client = session.client("ssm")
        stubber = Stubber(ssm_client)
        _ = mocker.patch.object(main, "_create_ssm_client", autospec=True, return_value=ssm_client)
        describe_response = {
            "InstanceInformationList": [{"InstanceId": expected_instance_id}],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        expected_describe_params = {"Filters": [{"Key": "IamRole", "Values": [expected_role_name]}]}
        stubber.add_response("describe_instance_information", describe_response, expected_describe_params)
        add_tags_params = {
            "ResourceType": "ManagedInstance",
            "ResourceId": expected_instance_id,
            "Tags": [{"Key": INSTALLED_AGENT_VERSION_TAG_KEY, "Value": expected_version}],
        }
        stubber.add_response("add_tags_to_resource", {"ResponseMetadata": {"HTTPStatusCode": 200}}, add_tags_params)

        stubber.activate()

        cli_args = parser.parse_args(
            [
                f"--stop-flag-dir={self.flag_file_dir}",
                "--shut-down-before-main-loop",
                "--aws-region",
                random_region,
            ]
        )

        assert start_courier(cli_args, stop_event=threading.Event()) == 0

        stubber.assert_no_pending_responses()

        # Due to the way the Stubber works with the expected_params, the test would fail if the describe_instance_information method is called with a different role name than the one we are expecting
        # Due to the way the Stubber works with the expected_params, the test would fail if the add_tags_to_resource method is called with a different InstanceId that the one we are expecting


class TestShutdown(MainMixin):
    @pytest.mark.timeout(10)
    @pytest.mark.usefixtures(mocked_generic_config.__name__)
    def test_Given_no_files_to_upload__When_flag_file_created__Then_clean_exit(self, mocker: MockerFixture):
        _ = mocker.patch.object(  # updating the instance tag has no bearing on the logic under test here, so patching it
            main,
            main._update_instance_tag.__name__,  # noqa: SLF001 # yes, this is private, but we're just patching the function to prevent it from running
            autospec=True,
        )
        cli_args = parser.parse_args(
            [
                f"--stop-flag-dir={self.flag_file_dir}",
                "--aws-region=us-east-1",
                "--idle-loop-sleep-seconds=0.1",
            ]
        )
        thread = Thread(target=start_courier, args=(cli_args,), kwargs={"stop_event": threading.Event()})
        thread.start()
        # also make a subdirectory, just to test the logic that nothing happens
        (Path(self.flag_file_dir) / str(uuid.uuid4())).mkdir()
        flag_file = Path(self.flag_file_dir) / f"{uuid.uuid4()}.txt"

        flag_file.touch()
        thread.join(timeout=5)

        assert thread.is_alive() is False

    @pytest.mark.timeout(10)
    @pytest.mark.usefixtures(mocked_generic_config.__name__)
    def test_Given_agent_running__When_stop_event_set__Then_clean_exit(self, mocker: MockerFixture):
        _ = mocker.patch.object(
            main,
            main._update_instance_tag.__name__,  # noqa: SLF001 # patched only to keep it from running; it is covered by its own test
            autospec=True,
        )
        stop_event = threading.Event()
        cli_args = parser.parse_args(
            [
                f"--stop-flag-dir={self.flag_file_dir}",
                "--aws-region=us-east-1",
                "--idle-loop-sleep-seconds=0.1",
            ]
        )
        thread = Thread(target=start_courier, args=(cli_args,), kwargs={"stop_event": stop_event})
        thread.start()
        assert thread.is_alive() is True

        stop_event.set()
        thread.join(timeout=5)

        assert thread.is_alive() is False
