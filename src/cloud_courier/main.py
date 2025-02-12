import argparse
import functools
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from queue import SimpleQueue

import boto3
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer

from .aws_credentials import create_boto_session
from .aws_credentials import get_role_arn
from .logger_config import configure_logging

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


def event_handler(file_system_events: SimpleQueue[FileSystemEvent], event: FileSystemEvent):
    file_system_events.put(event)


class MainLoop:
    def __init__(self, *, stop_flag_dir: str, boto_session: boto3.Session, idle_loop_sleep_seconds: float):
        super().__init__()
        self.stop_flag_dir = Path(stop_flag_dir)
        self.boto_session = boto_session
        self.idle_loop_sleep_seconds = idle_loop_sleep_seconds
        self.file_system_events: SimpleQueue[FileSystemEvent] = SimpleQueue()
        self.observers: list[Observer] = []  # type: ignore[reportInvalidTypeForm] # pyright doesn't seem to like Observer
        self.event_handler = functools.partial(event_handler, self.file_system_events)

    def run(self) -> int:
        self.observers.append(Observer())  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.observers[0].schedule(self.event_handler, self.stop_flag_dir, recursive=False)  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        self.observers[0].start()  # type: ignore[reportUnknownMemberType] # pyright doesn't seem to like Observer
        while True:
            if any(item.is_file() for item in self.stop_flag_dir.iterdir()):
                for item in self.stop_flag_dir.iterdir():
                    if item.is_file():
                        logger.info(f"Found stop flag file: {item}. Deleting it now")
                        item.unlink()
                break
            logger.info(f"Connected to AWS as: {get_role_arn(self.boto_session)}")
            time.sleep(self.idle_loop_sleep_seconds)
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
        return MainLoop(
            stop_flag_dir=cli_args.stop_flag_dir,
            boto_session=boto_session,
            idle_loop_sleep_seconds=cli_args.idle_loop_sleep_seconds,
        ).run()
    except Exception:
        logger.exception("An unhandled exception occurred")
        raise
