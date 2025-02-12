import tempfile
import time
import uuid
from copy import deepcopy
from pathlib import Path
from threading import Thread
from unittest.mock import ANY

import boto3
import pytest
from pytest_mock import MockerFixture

from cloud_courier import MainLoop
from cloud_courier import load_config_from_aws
from cloud_courier import main
from cloud_courier import upload_to_s3

from .constants import GENERIC_COURIER_CONFIG
from .fixtures import mocked_generic_config

_fixtures = (mocked_generic_config,)


class TestFolderMonitoring:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        self.boto_session = boto3.Session(region_name=GENERIC_COURIER_CONFIG.aws_region)
        self.mocker = mocker
        with tempfile.TemporaryDirectory() as stop_flag_dir:
            with tempfile.TemporaryDirectory() as watch_dir:
                self.watch_dir = watch_dir
                self.config = deepcopy(GENERIC_COURIER_CONFIG)
                self.config.folders_to_watch["fcs-files"] = self.config.folders_to_watch["fcs-files"].model_copy(
                    update={"folder_path": watch_dir}
                )
                self.folder_config = self.config.folders_to_watch["fcs-files"]
                _ = mocker.patch.object(main, load_config_from_aws.__name__, autospec=True, return_value=self.config)
                self.loop = MainLoop(
                    boto_session=self.boto_session, stop_flag_dir=stop_flag_dir, idle_loop_sleep_seconds=0.1
                )
                thread = Thread(
                    target=self.loop.run,
                )
                thread.start()
                yield
            (Path(stop_flag_dir) / str(uuid.uuid4())).mkdir()
            flag_file = Path(stop_flag_dir) / f"{uuid.uuid4()}.txt"

            flag_file.touch()
            thread.join(timeout=5)

        assert thread.is_alive() is False

    def test_When_file_created_by_opening_and_closing__Then_uploaded_and_added_to_internal_memory(self):
        file_path = Path(self.watch_dir) / f"{uuid.uuid4()!s}.txt"
        expected_checksum = str(uuid.uuid4())
        mocked_upload_to_s3 = self.mocker.patch.object(
            main, upload_to_s3.__name__, autospec=True, return_value=expected_checksum
        )
        with file_path.open("w") as file:
            _ = file.write("test")

        for _ in range(50):
            if file_path in self.loop.uploaded_files:
                break
            time.sleep(0.01)
        else:
            pytest.fail("File was not uploaded")

        mocked_upload_to_s3.assert_called_once_with(
            file_path=file_path,
            boto_session=ANY,
            bucket_name=self.folder_config.s3_bucket_name,
            object_key=f"{self.folder_config.s3_key_prefix}{file_path}",
        )
