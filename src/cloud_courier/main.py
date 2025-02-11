import argparse
import logging

import boto3

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
_ = parser.add_argument(
    "--use-generic-boto-session",
    action="store_true",
    help="Use a generic boto3 session instead of attempting to use the SSM credentials. Useful for testing.",
)


def main(argv: list[str]) -> int:
    configure_logging()
    try:
        cli_args = parser.parse_args(argv)
    except argparse.ArgumentError:
        logger.exception("Error parsing command line arguments")
        return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse

    boto3_session = boto3.Session() if cli_args.use_generic_boto_session else create_boto_session(cli_args.aws_region)
    sts_client = boto3_session.client("sts")
    if cli_args.immediate_shut_down:
        logger.info("Exiting due to --immediate-shut-down")
        return 0
    logger.info(f"Connected to AWS as: {sts_client.get_caller_identity()}")
    return 0
