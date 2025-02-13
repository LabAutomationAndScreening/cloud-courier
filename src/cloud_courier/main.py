import argparse
import logging
import queue
import threading
import time
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
from .courier_config_models import FolderToWatch
from .load_config import CourierConfig
from .load_config import load_config_from_aws
from .logger_config import configure_logging
from .upload import convert_path_to_s3_object_key
from .upload import upload_to_s3

type Checksum = str
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(description="cloud-courier", exit_on_error=False)
_ = parser.add_argument(
    "--aws-region",
    required=True,
    type=str,
    help="The AWS Region the cloud-courier infrastructure is deployed to (e.g. us-east-1).",
)
_ = parser.add_argument(
    "--immediate-shut-down",
    action="store_true",
    help="Shut down the system before actually doing anything meaningful. Useful for unit testing.",
)
_ = parser.add_argument(
    "--use-generic-boto-session",
    action="store_true",
    help="Use a generic boto3 session instead of attempting to use the SSM credentials. Useful for testing.",
)
_ = parser.add_argument(
    "--stop-flag-dir",
    type=str,
    help="The directory where the program looks for flag files (e.g. telling it to shut down).",
    required=True,
)
_ = parser.add_argument(
    "--idle-loop-sleep-seconds",
    type=float,
    help="The number of seconds to sleep between iterations of the main loop if there are no files to upload.",
    default=5,
)
_ = parser.add_argument("--log-level", type=str, default="INFO", help="The log level to use for the logger")


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
    def __init__(self, *, stop_flag_dir: str, boto_session: boto3.Session, idle_loop_sleep_seconds: float):
        super().__init__()
        self.stop_flag_dir = Path(stop_flag_dir)
        self.boto_session = boto_session
        self._idle_loop_sleep_seconds = idle_loop_sleep_seconds
        self.file_system_events: SimpleQueue[tuple[FileSystemEvent, FolderToWatch]]
        self.observers: list[Observer] = []  # type: ignore[reportInvalidTypeForm] # pyright doesn't seem to like Observer
        self.event_handler: EventHandler
        self.config: CourierConfig
        self.uploaded_files: dict[Path, Checksum]
        self.main_loop_entered = threading.Event()  # helpful for unit testing

    def _boot_up(self):
        """Perform initial activities before starting passive monitoring.

        This happens when the loop first starts, and also after any difference is detected in the configuration.
        """
        self.file_system_events = SimpleQueue()
        self.observers.clear()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer

        self.config = load_config_from_aws(self.boto_session)
        self.uploaded_files = {}
        # TODO: check all the folders and raise an error if any don't exist

    def _upload_file(self, file_path: Path, folder_config: FolderToWatch):
        self.uploaded_files[file_path] = upload_to_s3(
            file_path=file_path,
            boto_session=self.boto_session,
            bucket_name=folder_config.s3_bucket_name,
            object_key=convert_path_to_s3_object_key(str(file_path), folder_config),
        )

    def _process_file_event_queue(self):
        try:
            event, folder_config = self.file_system_events.get(timeout=0.5)
        except queue.Empty:
            return
        assert isinstance(event.src_path, str), (
            f"Expected event.src_path to be a string, but got {event.src_path} of type {type(event.src_path)}"
        )
        self._upload_file(Path(event.src_path), folder_config)

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
        while True:
            self.main_loop_entered.set()
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
        ).run()
    except Exception:
        logger.exception("An unhandled exception occurred")
        raise
