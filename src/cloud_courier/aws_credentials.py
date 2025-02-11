import configparser
import datetime
import os
from pathlib import Path
from typing import TypedDict


class AwsCredentialsMetadata(TypedDict):
    access_key: str
    secret_key: str
    token: str
    expiry_time: str


def path_to_aws_credentials() -> Path:
    # https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent-technical-details.html
    if (
        os.name == "nt"
    ):  # pragma: no cover # In Linux test environments, pathlib throws an error trying to run this: cannot instantiate 'WindowsPath' on your system
        return Path("C:") / "Windows" / "System32" / "config" / "systemprofile" / ".aws" / "credentials"
    return (  # pragma: no cover # In Windows test environments, pathlib will probably throw an error about this
        Path("/var") / "lib" / "amazon" / "ssm" / "credentials"
    )


def read_aws_creds() -> AwsCredentialsMetadata:
    config = configparser.ConfigParser()
    _ = config.read(path_to_aws_credentials())

    creds = config["default"]

    access_key = creds["aws_access_key_id"]
    secret_key = creds["aws_secret_access_key"]
    token = creds["aws_session_token"]
    # According to this, credentials are rotated every 30 minutes, so set the expiry to 25 https://github.com/aws/amazon-ssm-agent/issues/570
    expiry_time = (datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=25)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return AwsCredentialsMetadata(access_key=access_key, secret_key=secret_key, token=token, expiry_time=expiry_time)
