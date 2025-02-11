import argparse
import logging
import time
from pathlib import Path

import boto3

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


class MainLoop:
    def __init__(self, *, stop_flag_dir: str, boto_session: boto3.Session, idle_loop_sleep_seconds: float):
        super().__init__()
        self.stop_flag_dir = Path(stop_flag_dir)
        self.boto_session = boto_session
        self.idle_loop_sleep_seconds = idle_loop_sleep_seconds

    def run(self) -> int:
        while True:
            if any(item.is_file() for item in self.stop_flag_dir.iterdir()):
                for item in self.stop_flag_dir.iterdir():
                    if item.is_file():
                        logger.info(f"Found stop flag file: {item}. Deleting it now")
                        item.unlink()
                return 0

            time.sleep(self.idle_loop_sleep_seconds)


def main(argv: list[str]) -> int:
    configure_logging()
    try:
        cli_args = parser.parse_args(argv)
    except argparse.ArgumentError:
        logger.exception("Error parsing command line arguments")
        return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse

    boto3_session = boto3.Session() if cli_args.use_generic_boto_session else create_boto_session(cli_args.aws_region)
    if cli_args.immediate_shut_down:
        logger.info("Exiting due to --immediate-shut-down")
        return 0
    logger.info(f"Connected to AWS as: {get_role_arn(boto3_session)}")
    return MainLoop(
        stop_flag_dir=cli_args.stop_flag_dir,
        boto_session=boto3_session,
        idle_loop_sleep_seconds=cli_args.idle_loop_sleep_seconds,
    ).run()
