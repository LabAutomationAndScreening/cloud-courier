import argparse
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
from watchdog.events import FileClosedEvent
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .aws_credentials import create_boto_session
from .aws_credentials import get_role_arn
from .cli import parser
from .constants import Checksum
from .courier_config_models import FolderToWatch
from .load_config import CourierConfig
from .load_config import load_config_from_aws
from .logger_config import configure_logging
from .upload import convert_path_to_s3_object_key
from .upload import upload_to_s3

logger = logging.getLogger(__name__)


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
        self, *, file_system_events: SimpleQueue[tuple[FileSystemEvent, FolderToWatch]], folder_config: FolderToWatch
    ):
        super().__init__()
        self.file_system_events = file_system_events
        self.folder_config = folder_config

    @override
    def on_any_event(self, event: FileSystemEvent) -> None:
        logger.debug(event)

    @override
    def on_closed(self, event: FileClosedEvent) -> None:
        self.file_system_events.put((event, self.folder_config))


class MainLoop:
    def __init__(
        self,
        *,
        stop_flag_dir: str,
        boto_session: boto3.Session,
        idle_loop_sleep_seconds: float,
        previously_uploaded_files_record_path: Path,
    ):
        super().__init__()
        self.previously_uploaded_files_record_path = previously_uploaded_files_record_path
        self.stop_flag_dir = Path(stop_flag_dir)
        self.boto_session = boto_session
        self._idle_loop_sleep_seconds = idle_loop_sleep_seconds
        self.file_system_events: SimpleQueue[tuple[FileSystemEvent, FolderToWatch]]
        self.observers: list[Observer] = []  # type: ignore[reportInvalidTypeForm] # pyright doesn't seem to like Observer
        self.event_handler: EventHandler
        self.config: CourierConfig
        self.main_loop_entered = threading.Event()  # helpful for unit testing
        create_record_file(self.previously_uploaded_files_record_path)
        self.uploaded_files = parse_upload_record(self.previously_uploaded_files_record_path)

    def _boot_up(self):
        """Perform initial activities before starting passive monitoring.

        This happens when the loop first starts, and also after any difference is detected in the configuration.
        """
        self.file_system_events = SimpleQueue()
        self.observers.clear()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer

        self.config = load_config_from_aws(self.boto_session)
        # TODO: check all the folders and raise an error if any don't exist
        # TODO: implement refreshing the config

        folder_config = next(iter(self.config.folders_to_watch.values()))  # TODO: support multiple folders to search
        folder_path = Path(folder_config.folder_path)
        glob_path = "*"
        if folder_config.recursive:
            glob_path = "**/*"
        for file in folder_path.glob(glob_path):
            if file.is_file():
                # This isn't truly a FileClosedEvent, but it's easier to just have a single codepath for all uploading
                self.file_system_events.put((FileClosedEvent(src_path=str(file)), folder_config))

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
            event, folder_config = self.file_system_events.get(timeout=0.5)
        except queue.Empty:
            return
        assert isinstance(event.src_path, str), (
            f"Expected event.src_path to be a string, but got {event.src_path} of type {type(event.src_path)}"
        )
        file_path = Path(event.src_path)
        if file_path in self.uploaded_files:
            logger.info(f"Skipping {file_path} because it has already been uploaded")
            return  # TODO: decide how to handle changes to the file that alter the checksum
        self._upload_file(file_path, folder_config)

    def run(self) -> int:
        self._boot_up()
        self.observers.append(Observer())  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        folder_config = next(iter(self.config.folders_to_watch.values()))
        folder_path = folder_config.folder_path
        self.observers[0].schedule(  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
            EventHandler(file_system_events=self.file_system_events, folder_config=folder_config),
            folder_path,
            recursive=folder_config.recursive,
        )
        self.observers[0].start()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.main_loop_entered.set()
        while True:
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

            time.sleep(self._idle_loop_sleep_seconds)
        self.observers[0].stop()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.observers[0].join()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        return 0


def entrypoint(argv: Sequence[str]) -> int:
    try:
        try:
            cli_args = parser.parse_args(argv)
        except argparse.ArgumentError:
            logger.exception("Error parsing command line arguments")
            return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse
        configure_logging(log_level=cli_args.log_level)
        logger.info('Starting "cloud-courier"')
        boto_session = (
            boto3.Session() if cli_args.use_generic_boto_session else create_boto_session(cli_args.aws_region)
        )
        if cli_args.immediate_shut_down:
            logger.info("Exiting due to --immediate-shut-down")
            return 0
        logger.info(f"Connected to AWS as: {get_role_arn(boto_session)}")
        # TODO: send SNS alert if error within main loop (until heartbeat and cloudwatch set up)
        return MainLoop(
            stop_flag_dir=cli_args.stop_flag_dir,
            boto_session=boto_session,
            idle_loop_sleep_seconds=cli_args.idle_loop_sleep_seconds,
            previously_uploaded_files_record_path=path_to_previously_uploaded_files_record(),
        ).run()
    except Exception:
        logger.exception("An unhandled exception occurred")
        raise
