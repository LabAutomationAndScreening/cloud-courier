import argparse
import logging

from .aws_credentials import create_boto_session
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


def main(argv: list[str]) -> int:
    configure_logging()
    try:
        cli_args = parser.parse_args(argv)
    except argparse.ArgumentError:
        logger.exception("Error parsing command line arguments")
        return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse

    _ = create_boto_session(cli_args.aws_region)
    return 0
