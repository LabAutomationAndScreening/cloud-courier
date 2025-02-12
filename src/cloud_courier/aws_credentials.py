import configparser
import datetime
import logging
import os
from pathlib import Path
from typing import TypedDict

import boto3
import botocore.session
from botocore.credentials import RefreshableCredentials

logger = logging.getLogger(__name__)


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
    creds_path = path_to_aws_credentials()
    logger.debug(f'Attempting to read AWS credentials from "{creds_path}"')
    _ = config.read(creds_path)
    try:
        creds = config["default"]
    except KeyError:
        logger.exception(
            f'Error attempting to read AWS credentials from "{creds_path}". There was no "default" section in {config!r}'
        )
        raise

    access_key = creds["aws_access_key_id"]
    secret_key = creds["aws_secret_access_key"]
    token = creds["aws_session_token"]
    # According to this, credentials are rotated every 30 minutes, so set the expiry to 25 https://github.com/aws/amazon-ssm-agent/issues/570
    expiry_time = (datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=25)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return AwsCredentialsMetadata(access_key=access_key, secret_key=secret_key, token=token, expiry_time=expiry_time)


def refresh_credentials() -> (  # pragma: no cover # This is a callback function that I'm not sure exactly how to test. But the underlying read_aws_creds() is tested
    AwsCredentialsMetadata
):
    logger.info("Refreshing AWS credentials")
    return read_aws_creds()


def create_boto_session(aws_region: str) -> boto3.Session:
    initial_credentials = read_aws_creds()

    refreshable_creds = RefreshableCredentials.create_from_metadata(
        metadata=initial_credentials,  # type: ignore[reportArgumentType] # pyright thinks this should accept dict[str, Any] ... but it seems like the TypedDict should be a valid subset of that
        refresh_using=refresh_credentials,
        method="custom-refresh",
    )

    botocore_session = botocore.session.get_session()
    botocore_session._credentials = refreshable_creds  # type:ignore[reportAttributeAccessIssue] # noqa: SLF001 # assigning directly to the private variable is the recommended approach for refreshable credentials. # pyright thinks this should accept dict[str, Any] ... but it seems like the TypedDict should be a valid subset of that
    botocore_session.set_config_variable("region", aws_region)  # Set your desired region
    return boto3.Session(botocore_session=botocore_session)


def get_role_arn(session: boto3.Session) -> str:
    sts_client = session.client("sts")
    return sts_client.get_caller_identity()["Arn"]
