import argparse
from importlib.metadata import version


def get_version() -> str:
    return f"v{version('cloud-courier')}"


parser = argparse.ArgumentParser(description="cloud-courier", exit_on_error=False)
_ = parser.add_argument("--version", action="version", version=get_version())

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
_ = parser.add_argument("--log-folder", type=str, help="The folder to write logs to")
_ = parser.add_argument(
    "--no-console-logging",
    action="store_true",
    help="Suppress console logging. Useful for some SSM Run commands.",
)
