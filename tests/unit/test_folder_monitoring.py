import shutil
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
from cloud_courier import add_to_upload_record
from cloud_courier import calculate_aws_checksum
from cloud_courier import create_record_file
from cloud_courier import load_config_from_aws
from cloud_courier import main
from cloud_courier import parse_upload_record
from cloud_courier import upload_to_s3

from .constants import GENERIC_COURIER_CONFIG
from .fixtures import mocked_generic_config

_fixtures = (mocked_generic_config,)


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


class TestFolderMonitoring(MainLoopMixin):
    def test_When_file_created_by_opening_and_closing__Then_mock_uploaded_with_correct_args_and_added_to_internal_memory(
        self,
    ):
        file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
        expected_checksum = str(uuid.uuid4())
        mocked_upload_to_s3 = self.mocker.patch.object(
            main, upload_to_s3.__name__, autospec=True, return_value=expected_checksum
        )
        self._start_loop(mock_upload_to_s3=False)

        with file_path.open("w") as file:
            _ = file.write("test")

        self._fail_if_file_not_uploaded(file_path)
        mocked_upload_to_s3.assert_called_once_with(
            file_path=file_path,
            boto_session=ANY,
            bucket_name=self.folder_config.s3_bucket_name,
            object_key=f"{self.folder_config.s3_key_prefix}{file_path}",
        )

    def test_When_file_created_by_copying__Then_mock_uploaded(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_file_path = Path(temp_dir) / f"{uuid.uuid4()}.txt"
            with original_file_path.open("w") as file:
                _ = file.write("test")

            file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
            self._start_loop()
            shutil.copy(original_file_path, file_path)

        self._fail_if_file_not_uploaded(file_path)

    @pytest.mark.xfail(
        reason="This only triggers a FileCreatedEvent...and we need to handle some short delays before uploading before supporting that...since everything triggers a file created event"
    )
    def test_When_file_created_by_moving__Then_mock_uploaded(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_file_path = Path(temp_dir) / f"{uuid.uuid4()}.txt"
            with original_file_path.open("w") as file:
                _ = file.write("test")

            file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
            self._start_loop()
            shutil.move(original_file_path, file_path)

        self._fail_if_file_not_uploaded(file_path)

    def test_Given_folder_config_includes_subfolders__When_file_created_in_subfolder__Then_mock_uploaded(self):
        assert self.folder_config.recursive is True
        sub_dir = Path(self.watch_dir) / str(uuid.uuid4())
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / f"{uuid.uuid4()}.txt"
        self._start_loop()

        with file_path.open("w") as file:
            _ = file.write("test")

        self._fail_if_file_not_uploaded(file_path)

    def test_Given_folder_config_excludes_subfolders__When_file_created_in_subfolder__Then_not_uploaded(self):
        self.config.folders_to_watch["fcs-files"] = self.config.folders_to_watch["fcs-files"].model_copy(
            update={"recursive": False}
        )
        sub_dir = Path(self.watch_dir) / str(uuid.uuid4())
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / f"{uuid.uuid4()}.txt"
        self._start_loop()

        with file_path.open("w") as file:
            _ = file.write("test")

        self._fail_if_file_uploaded(file_path)


class TestInitialFolderSearch(MainLoopMixin):
    def test_Given_folder_config_includes_subfolders__When_file_initially_exists_in_subfolders__Then_file_mock_uploaded_and_added_to_upload_record(
        self,
    ):
        assert self.folder_config.recursive is True
        sub_dir = Path(self.watch_dir) / str(uuid.uuid4())
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / f"{uuid.uuid4()}.txt"
        with file_path.open("w") as file:
            _ = file.write("test")

        self._start_loop()

        self._fail_if_file_not_uploaded(file_path)
        uploaded_files = parse_upload_record(self.upload_record_file_path)
        assert file_path in uploaded_files

    def test_Given_folder_config_does_not_include_subfolders__When_file_initially_exists_in_subfolders__Then_no_upload(
        self,
    ):
        self.config.folders_to_watch["fcs-files"] = self.config.folders_to_watch["fcs-files"].model_copy(
            update={"recursive": False}
        )
        sub_dir = Path(self.watch_dir) / str(uuid.uuid4())
        sub_dir.mkdir(parents=True, exist_ok=True)
        file_path = sub_dir / f"{uuid.uuid4()}.txt"
        with file_path.open("w") as file:
            _ = file.write("test")

        self._start_loop()

        self._fail_if_file_uploaded(file_path)

    def test_Given_file_already_in_uploaded_list__Then_no_upload(self):
        file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
        with file_path.open("w") as file:
            _ = file.write("test")
        create_record_file(self.upload_record_file_path)
        add_to_upload_record(
            record_file_path=self.upload_record_file_path,
            uploaded_file_path=file_path,
            checksum=calculate_aws_checksum(file_path),
            cloud_path=str(uuid.uuid4()),
        )

        self._start_loop()

        self._fail_if_any_file_uploaded()
