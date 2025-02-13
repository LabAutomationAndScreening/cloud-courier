import tempfile
import time
import uuid
from copy import deepcopy
from pathlib import Path
from threading import Thread

import boto3
import pytest
from pytest_mock import MockerFixture

from cloud_courier import CourierConfig
from cloud_courier import MainLoop
from cloud_courier import aws_credentials
from cloud_courier import load_config_from_aws
from cloud_courier import main
from cloud_courier import upload_to_s3
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX_TO_ALIASES

from .constants import GENERIC_COURIER_CONFIG
from .constants import PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS


@pytest.fixture
def mock_path_to_aws_credentials(mocker: MockerFixture):
    _ = mocker.patch.object(
        aws_credentials, "path_to_aws_credentials", autospec=True, return_value=PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS
    )


def store_config_in_aws(config: CourierConfig):
    ssm_client = boto3.client("ssm", region_name=config.aws_region)
    alias = config.role_name if config.alias_name is None else config.alias_name
    _ = ssm_client.put_parameter(
        Name=f"{SSM_PARAMETER_PREFIX_TO_ALIASES}/{config.role_name}",
        Value=alias,
        Type="String",
    )
    for descriptor, folder_to_watch in config.folders_to_watch.items():
        _ = ssm_client.put_parameter(
            Name=f"{SSM_PARAMETER_PREFIX}/{alias}/folders/{descriptor}",
            Value=folder_to_watch.model_dump_json(),
            Type="String",
        )


def cleanup_config_in_aws(config: CourierConfig):
    ssm_client = boto3.client("ssm", region_name=config.aws_region)
    alias = config.role_name if config.alias_name is None else config.alias_name
    _ = ssm_client.delete_parameter(Name=f"{SSM_PARAMETER_PREFIX_TO_ALIASES}/{config.role_name}")
    for descriptor in config.folders_to_watch:
        _ = ssm_client.delete_parameter(Name=f"{SSM_PARAMETER_PREFIX}/{alias}/folders/{descriptor}")


@pytest.fixture
def mocked_generic_config(mocker: MockerFixture):
    _ = mocker.patch.object(main, "load_config_from_aws", autospec=True, return_value=GENERIC_COURIER_CONFIG)


class MainLoopMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        self.boto_session = boto3.Session(region_name=GENERIC_COURIER_CONFIG.aws_region)
        self.mocker = mocker
        with (
            tempfile.TemporaryDirectory() as stop_flag_dir,
            tempfile.TemporaryDirectory() as watch_dir,
            tempfile.TemporaryDirectory() as record_dir,
        ):
            self.watch_dir = watch_dir
            self.stop_flag_dir = stop_flag_dir
            self.config = deepcopy(GENERIC_COURIER_CONFIG)
            self.config.folders_to_watch["fcs-files"] = self.config.folders_to_watch["fcs-files"].model_copy(
                update={"folder_path": watch_dir}
            )
            self.folder_config = self.config.folders_to_watch["fcs-files"]
            _ = mocker.patch.object(main, load_config_from_aws.__name__, autospec=True, return_value=self.config)
            self.upload_record_file_path = Path(record_dir) / str(uuid.uuid4()) / "record.tsv"

            yield

            (Path(stop_flag_dir) / str(uuid.uuid4())).mkdir(parents=True)
            flag_file = Path(stop_flag_dir) / f"{uuid.uuid4()}.txt"

            flag_file.touch()
            self.thread.join(timeout=5)

        assert self.thread.is_alive() is False

    def _start_loop(self, *, mock_upload_to_s3: bool = True):
        self.spied_upload_file = self.mocker.spy(MainLoop, "_upload_file")
        self.loop = MainLoop(
            boto_session=self.boto_session,
            stop_flag_dir=self.stop_flag_dir,
            idle_loop_sleep_seconds=0.1,
            previously_uploaded_files_record_path=self.upload_record_file_path,
        )
        if mock_upload_to_s3:
            _ = self.mocker.patch.object(main, upload_to_s3.__name__, autospec=True, return_value=str(uuid.uuid4()))
        self.thread = Thread(
            target=self.loop.run,
        )
        self.thread.start()
        for _ in range(50):
            if self.loop.main_loop_entered.is_set():
                break
            time.sleep(0.01)
        else:
            pytest.fail("Loop never entered")

    def _fail_if_file_uploaded(self, file_path: Path):
        for _ in range(200):
            if file_path in self.loop.uploaded_files:
                pytest.fail("File was uploaded")
            time.sleep(0.01)

    def _fail_if_any_file_uploaded(self):
        for _ in range(200):
            if self.spied_upload_file.call_count > 0:
                pytest.fail("File was uploaded")
            time.sleep(0.01)

    def _fail_if_file_not_uploaded(self, file_path: Path):
        for _ in range(50):
            if file_path in self.loop.uploaded_files:
                break
            time.sleep(0.01)
        else:
            pytest.fail("File was not uploaded")
