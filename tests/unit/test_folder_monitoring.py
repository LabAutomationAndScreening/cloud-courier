import shutil
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import ANY

import pytest

from cloud_courier import add_to_upload_record
from cloud_courier import calculate_aws_checksum
from cloud_courier import create_record_file
from cloud_courier import main
from cloud_courier import parse_upload_record
from cloud_courier import upload_to_s3

from .fixtures import MainLoopMixin
from .fixtures import mocked_generic_config

_fixtures = (mocked_generic_config,)


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

    def test_When_info_appended_to_file__Then_mock_uploaded(
        self,
    ):
        file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
        with file_path.open("w") as file:
            _ = file.write("test")

        self._start_loop()
        with file_path.open("a") as file:
            _ = file.write("test")

        self._fail_if_file_not_uploaded(file_path)

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
        file_path = sub_dir / f"{uuid.uuid4()}.txt"

        self._start_loop()
        sub_dir.mkdir(  # make directory after starting loop to exercise that DirCreatedEvent is successfully ignored
            parents=True, exist_ok=True
        )
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

    def test_When_multiple_file_system_events_triggered_in_rapid_succession__Then_only_single_upload(
        self,
    ):
        file_path = Path(self.watch_dir) / f"{uuid.uuid4()}.txt"
        min_expected_events = 3
        with file_path.open("w") as file:
            _ = file.write("test")

        self._start_loop(create_duplicate_event_stream_for_test_monitoring=True)
        with file_path.open("a") as file:
            _ = file.write("test")

        # confirm multiple events were triggered
        for _ in range(200):
            if self.loop.file_system_events_for_test_monitoring.qsize() >= min_expected_events:
                break
            time.sleep(0.01)
        assert self.loop.file_system_events_for_test_monitoring.qsize() >= min_expected_events

        for _ in range(200):
            if self.loop.file_system_events.empty():
                break
            time.sleep(0.01)
        else:
            pytest.fail("Event queue never became empty")
        time.sleep(0.1)  # wait a tiny bit extra after no more events in queue for last one to be processed

        assert self.spied_upload_file.call_count == 1


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
