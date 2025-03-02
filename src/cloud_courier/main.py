import argparse
import datetime
import logging
import os
import queue
import threading
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from queue import SimpleQueue
from typing import override

import boto3
from mypy_boto3_ssm.client import SSMClient
from pydantic import BaseModel
from pydantic import Field
from watchdog.events import DirCreatedEvent
from watchdog.events import DirModifiedEvent
from watchdog.events import FileClosedEvent
from watchdog.events import FileCreatedEvent
from watchdog.events import FileModifiedEvent
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .aws_credentials import create_boto_session
from .aws_credentials import get_role_arn
from .cli import get_version
from .cli import parser
from .constants import Checksum
from .courier_config_models import CLOUDWATCH_HEARTBEAT_NAMESPACE
from .courier_config_models import CLOUDWATCH_INSTANCE_ID_DIMENSION_NAME
from .courier_config_models import HEARTBEAT_METRIC_NAME
from .courier_config_models import FolderToWatch
from .load_config import CourierConfig
from .load_config import extract_role_name_from_arn
from .load_config import load_config_from_aws
from .logger_config import configure_logging
from .upload import convert_path_to_s3_object_key
from .upload import upload_to_s3

RESET_POINT_FOR_LOOP_ITERATION_COUNTER = 20  # this is only for assertions in unit tests, so just reset the value if it gets arbitrarily high so that it doesn't cause an overflow when running in production
INSTALLED_AGENT_VERSION_TAG_KEY = "installed-cloud-courier-agent-version"  # Warning! This tag key is originally created by the cloud-courier-infrastructure Pulumi code, so don't change it here without changing it there
logger = logging.getLogger(__name__)


class FileEventInfo(BaseModel, frozen=True):
    file_system_event: FileSystemEvent
    folder_config: FolderToWatch
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(tz=datetime.UTC))


def path_to_previously_uploaded_files_record() -> Path:
    if (
        os.name == "nt"
    ):  # pragma: no cover # In Linux test environments, pathlib throws an error trying to run this: cannot instantiate 'WindowsPath' on your system
        return (
            Path("C:\\")
            / "ProgramData"
            / "LabAutomationAndScreening"
            / "CloudCourier"
            / "previously_uploaded_files.tsv"
        )
    return (  # pragma: no cover # In Windows test environments, pathlib will probably throw an error about this
        Path("~/") / ".lab_automation_and_screening" / "cloud_courier" / "previously_uploaded_files.tsv"
    )


def create_record_file(record_file_path: Path):
    if record_file_path.exists():
        return

    parent_dir = record_file_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    with record_file_path.open("w") as f:
        _ = f.write("file_path\tcloud_path\tchecksum\n")


def add_to_upload_record(*, record_file_path: Path, uploaded_file_path: Path, checksum: str, cloud_path: str):
    with record_file_path.open("a") as f:
        _ = f.write(f"{uploaded_file_path}\t{cloud_path}\t{checksum}\n")


def parse_upload_record(record_file_path: Path) -> dict[Path, set[Checksum]]:
    uploaded_files: dict[Path, set[Checksum]] = defaultdict(set)
    with record_file_path.open("r") as f:
        for line_idx, line in enumerate(f):
            if line_idx == 0:
                continue  # skip header
            file_path, _, checksum = line.strip().split("\t")
            uploaded_files[Path(file_path)].add(checksum)
    return uploaded_files


class EventHandler(FileSystemEventHandler):
    def __init__(
        self,
        *,
        file_system_events: SimpleQueue[FileEventInfo],
        folder_config: FolderToWatch,
        file_system_events_for_test_monitoring: SimpleQueue[FileEventInfo] | None = None,
    ):
        super().__init__()
        self.file_system_events = file_system_events
        self.folder_config = folder_config
        self.file_system_events_for_test_monitoring = file_system_events_for_test_monitoring

    @override
    def on_any_event(self, event: FileSystemEvent) -> None:
        logger.critical(f"{event} at {datetime.datetime.now(tz=datetime.UTC)}")

    # FileCreatedEvent and FileModifiedEvent are prevalent on Windows
    @override
    def on_closed(self, event: FileClosedEvent) -> None:
        self._add_event_to_queue(event)

    @override
    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        if isinstance(event, DirCreatedEvent):
            return
        self._add_event_to_queue(event)

    @override
    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        if isinstance(event, DirModifiedEvent):
            return
        self._add_event_to_queue(event)

    def _add_event_to_queue(self, event: FileSystemEvent):
        event_info = FileEventInfo(file_system_event=event, folder_config=self.folder_config)
        self.file_system_events.put(event_info)
        if self.file_system_events_for_test_monitoring is not None:
            self.file_system_events_for_test_monitoring.put(event_info)


class MainLoop:
    def __init__(
        self,
        *,
        stop_flag_dir: str,
        boto_session: boto3.Session,
        idle_loop_sleep_seconds: float,
        previously_uploaded_files_record_path: Path,
        create_duplicate_event_stream_for_test_monitoring: bool = False,
    ):
        super().__init__()
        self.num_loop_iterations = 0
        self.create_duplicate_event_stream_for_test_monitoring = create_duplicate_event_stream_for_test_monitoring
        self.previously_uploaded_files_record_path = previously_uploaded_files_record_path
        self.stop_flag_dir = Path(stop_flag_dir)
        self.boto_session = boto_session
        self._idle_loop_sleep_seconds = idle_loop_sleep_seconds
        self.file_system_events: SimpleQueue[FileEventInfo]
        self.file_system_events_for_test_monitoring: SimpleQueue[FileEventInfo]
        self.observers: list[Observer] = []  # type: ignore[reportInvalidTypeForm] # pyright doesn't seem to like Observer
        self.event_handler: EventHandler
        self.config: CourierConfig
        self.main_loop_entered = threading.Event()  # helpful for unit testing
        create_record_file(self.previously_uploaded_files_record_path)
        self.uploaded_files = parse_upload_record(self.previously_uploaded_files_record_path)
        self.last_heartbeat_timestamp = datetime.datetime(
            year=1988, month=1, day=19, tzinfo=datetime.UTC
        )  # infinitely long ago

    def _send_heartbeat_if_needed(self):
        current_timestamp = datetime.datetime.now(tz=datetime.UTC)
        seconds_since_last_heartbeat = (current_timestamp - self.last_heartbeat_timestamp).total_seconds()
        if seconds_since_last_heartbeat >= self.config.app_config.heartbeat_frequency_seconds:
            self._send_heartbeat()
            self.last_heartbeat_timestamp = current_timestamp

    def _send_heartbeat(self):
        cloudwatch_client = self.boto_session.client("cloudwatch")
        _ = cloudwatch_client.put_metric_data(
            Namespace=CLOUDWATCH_HEARTBEAT_NAMESPACE,
            MetricData=[
                {
                    "MetricName": HEARTBEAT_METRIC_NAME,
                    "Dimensions": [
                        {"Name": "Application", "Value": "CloudCourier"},
                        {"Name": CLOUDWATCH_INSTANCE_ID_DIMENSION_NAME, "Value": self.config.role_name},
                    ],
                    "Timestamp": datetime.datetime.now(tz=datetime.UTC),
                    "Value": 1,
                    "Unit": "Count",
                },
            ],
        )
        logger.info("Sent heartbeat to CloudWatch")

    def _boot_up(self):
        """Perform initial activities before starting passive monitoring.

        This happens when the loop first starts, and also after any difference is detected in the configuration.
        """
        self.file_system_events = SimpleQueue()
        if self.create_duplicate_event_stream_for_test_monitoring:
            self.file_system_events_for_test_monitoring = SimpleQueue()
        self.observers.clear()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer

        self.config = load_config_from_aws(self.boto_session)
        # TODO: check all the folders and raise an error if any don't exist
        # TODO: implement refreshing the config
        self._send_heartbeat_if_needed()
        folder_config = next(iter(self.config.folders_to_watch.values()))  # TODO: support multiple folders to search
        folder_path = Path(folder_config.folder_path)
        glob_path = "*"
        if folder_config.recursive:
            glob_path = "**/*"
        for file in folder_path.glob(glob_path):
            if file.is_file():
                # This isn't truly a FileClosedEvent, but it's easier to just have a single codepath for all uploading
                event_info = FileEventInfo(
                    file_system_event=FileClosedEvent(src_path=str(file)), folder_config=folder_config
                )
                self.file_system_events.put(event_info)
                if self.create_duplicate_event_stream_for_test_monitoring:
                    self.file_system_events_for_test_monitoring.put(event_info)

    def _upload_file(self, file_path: Path, folder_config: FolderToWatch):
        object_key = convert_path_to_s3_object_key(str(file_path), folder_config)
        checksum = upload_to_s3(
            file_path=file_path,
            boto_session=self.boto_session,
            bucket_name=folder_config.s3_bucket_name,
            object_key=object_key,
        )
        self.uploaded_files[file_path].add(checksum)
        add_to_upload_record(
            record_file_path=self.previously_uploaded_files_record_path,
            uploaded_file_path=file_path,
            checksum=checksum,
            cloud_path=f"s3://{folder_config.s3_bucket_name}/{object_key}",
        )

    def _process_file_event_queue(self):
        try:
            event_info = self.file_system_events.get(timeout=0.05)
        except queue.Empty:
            return
        event = event_info.file_system_event

        seconds_since_event = (datetime.datetime.now(tz=datetime.UTC) - event_info.timestamp).total_seconds()
        if seconds_since_event < event_info.folder_config.delay_seconds_before_upload:
            logger.info(
                f"Skipping {event.src_path} because it was created less than {event_info.folder_config.delay_seconds_before_upload} seconds ago"
            )
            self.file_system_events.put(
                event_info
            )  # put it back in the queue to check again later if enough time has elapsed
            return

        assert isinstance(event.src_path, str), (
            f"Expected event.src_path to be a string, but got {event.src_path} of type {type(event.src_path)}"
        )
        file_path = Path(event.src_path)
        if file_path in self.uploaded_files:
            logger.info(f"Skipping {file_path} because it has already been uploaded")
            return  # TODO: decide how to handle changes to the file that alter the checksum
        self._upload_file(file_path, event_info.folder_config)

    def run(self) -> int:
        self._boot_up()
        self.observers.append(Observer())  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        folder_config = next(iter(self.config.folders_to_watch.values()))
        folder_path = folder_config.folder_path
        self.observers[0].schedule(  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
            EventHandler(
                file_system_events=self.file_system_events,
                folder_config=folder_config,
                file_system_events_for_test_monitoring=self.file_system_events_for_test_monitoring
                if self.create_duplicate_event_stream_for_test_monitoring
                else None,
            ),
            folder_path,
            recursive=folder_config.recursive,
        )
        self.observers[0].start()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.main_loop_entered.set()
        while True:
            self._send_heartbeat_if_needed()
            if any(
                item.is_file() for item in self.stop_flag_dir.iterdir()
            ):  # TODO: maybe use a separate observer for the stop file
                for item in self.stop_flag_dir.iterdir():
                    if item.is_file():
                        logger.info(f"Found stop flag file: {item}. Deleting it now")
                        item.unlink()
                break
            logger.info(f"Connected to AWS as: {get_role_arn(self.boto_session)}")
            self._process_file_event_queue()

            self._idle_loop_sleep()
            self.num_loop_iterations += 1
            if self.num_loop_iterations > RESET_POINT_FOR_LOOP_ITERATION_COUNTER:
                self.num_loop_iterations = 0
        self.observers[0].stop()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.observers[0].join()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        return 0

    def _idle_loop_sleep(self):
        # breaking out as separate method for easier testing
        time.sleep(self._idle_loop_sleep_seconds)  # TODO: dont sleep if there are events in the queue


def _create_ssm_client(boto_session: boto3.Session) -> SSMClient:
    # separate function for easy mocking in unit tests
    return boto_session.client(  # pragma: no cover # The SSM Client is always stubbed during tests, so this code never executes
        "ssm"
    )


def _update_instance_tag(*, boto_session: boto3.Session, role_arn: str):
    # CAUTION! This function is only tested using botocore stubbing, so be careful when changing it. Localstack does not have thorough support for SSM Instances
    role_name = extract_role_name_from_arn(role_arn)
    ssm_client = _create_ssm_client(boto_session)

    logger.critical(f"calling with role name: {role_name}")
    instance_info_response = ssm_client.describe_instance_information(
        Filters=[{"Key": "IamRole", "Values": [role_name]}]
    )
    instances = instance_info_response["InstanceInformationList"]
    assert len(instances) == 1, (
        f"Expected to find exactly one instance with role name {role_name}, but found {len(instances)}: {instances}"
    )  # TODO: explicitly unit test this piece of business logic
    instance = instances[0]
    assert "InstanceId" in instance, (
        f"Expected to find an instance ID in the instance information, but found {instance}"
    )
    instance_id = instance["InstanceId"]
    _ = ssm_client.add_tags_to_resource(
        ResourceType="ManagedInstance",
        ResourceId=instance_id,
        Tags=[
            {"Key": INSTALLED_AGENT_VERSION_TAG_KEY, "Value": get_version()},
        ],
    )


def entrypoint(argv: Sequence[str]) -> int:
    try:
        try:
            cli_args = parser.parse_args(argv)
        except argparse.ArgumentError:
            logger.exception("Error parsing command line arguments")
            return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse
        log_folder = Path("logs")
        if cli_args.log_folder is not None:
            log_folder = Path(cli_args.log_folder)
        configure_logging(
            log_level=cli_args.log_level,
            log_filename_prefix=str(log_folder / "cloud-courier-"),
            suppress_console_logging=bool(cli_args.no_console_logging),
        )  # TODO: move the logs folder into ProgramData by default
        logger.info('Starting "cloud-courier"')
        boto_session = (
            boto3.Session() if cli_args.use_generic_boto_session else create_boto_session(cli_args.aws_region)
        )
        if cli_args.immediate_shut_down:
            logger.info("Exiting due to --immediate-shut-down")
            return 0
        role_arn = get_role_arn(boto_session)
        logger.info(f"Connected to AWS as: {role_arn}")
        _update_instance_tag(boto_session=boto_session, role_arn=role_arn)
        if cli_args.shut_down_before_main_loop:
            logger.info("Exiting due to --shut-down-before-main-loop")
            return 0
        return MainLoop(
            stop_flag_dir=cli_args.stop_flag_dir,
            boto_session=boto_session,
            idle_loop_sleep_seconds=cli_args.idle_loop_sleep_seconds,
            previously_uploaded_files_record_path=path_to_previously_uploaded_files_record(),
        ).run()
    except Exception:
        logger.exception("An unhandled exception occurred")
        raise
