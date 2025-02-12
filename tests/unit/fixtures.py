from pathlib import Path

import boto3
import pytest
from pytest_mock import MockerFixture

from cloud_courier import AppConfig
from cloud_courier import CourierConfig
from cloud_courier import FolderToWatch
from cloud_courier import aws_credentials
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX_TO_ALIASES

PATH_TO_EXAMPLE_DATA_FILES = Path(__file__).parent.resolve() / "example_data_files"
PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS = Path(__file__).parent.resolve() / "example_windows_aws_creds.ini"

GENERIC_COURIER_CONFIG = CourierConfig(
    role_name="cambridge--cytation-5--cloud-courier--prod",
    alias_name="woburn--cytation-5--prod",
    app_config=AppConfig(),
    folders_to_watch={
        "fcs-files": FolderToWatch(
            folder_path=str(Path("C:/Users/username/Desktop/fcs-files")),
            s3_key_prefix="woburn/cytation-5",
            s3_bucket_name="my-bucket",
        )
    },
    aws_region="us-east-1",
)

COMPLEX_COURIER_CONFIG = CourierConfig(
    role_name="emeryville--star-1--cloud-courier--prod",
    app_config=AppConfig(),
    folders_to_watch={
        str(x): FolderToWatch(folder_path=str(x), s3_key_prefix="emeryville/star-1", s3_bucket_name="my-bucket")
        for x in range(100)
    },
    aws_region="us-west-1",
)


@pytest.fixture
def mock_path_to_aws_credentials(mocker: MockerFixture):
    _ = mocker.patch.object(
        aws_credentials, "path_to_aws_credentials", autospec=True, return_value=PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS
    )


def store_config_in_aws(config: CourierConfig):
    ssm_client = boto3.client("ssm", region_name=config.aws_region)
    alias = config.role_name if config.alias_name is None else config.alias_name
    _ = ssm_client.put_parameter(
        Name=f"{SSM_PARAMETER_PREFIX_TO_ALIASES}/{config.role_name}",
        Value=alias,
        Type="String",
    )
    for descriptor, folder_to_watch in config.folders_to_watch.items():
        _ = ssm_client.put_parameter(
            Name=f"{SSM_PARAMETER_PREFIX}/{alias}/folders/{descriptor}",
            Value=folder_to_watch.model_dump_json(),
            Type="String",
        )


def cleanup_config_in_aws(config: CourierConfig):
    ssm_client = boto3.client("ssm", region_name=config.aws_region)
    alias = config.role_name if config.alias_name is None else config.alias_name
    _ = ssm_client.delete_parameter(Name=f"{SSM_PARAMETER_PREFIX_TO_ALIASES}/{config.role_name}")
    for descriptor in config.folders_to_watch:
        _ = ssm_client.delete_parameter(Name=f"{SSM_PARAMETER_PREFIX}/{alias}/folders/{descriptor}")
