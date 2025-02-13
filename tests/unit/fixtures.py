import boto3
import pytest
from pytest_mock import MockerFixture

from cloud_courier import CourierConfig
from cloud_courier import aws_credentials
from cloud_courier import main
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX
from cloud_courier.courier_config_models import SSM_PARAMETER_PREFIX_TO_ALIASES

from .constants import GENERIC_COURIER_CONFIG
from .constants import PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS


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


@pytest.fixture
def mocked_generic_config(mocker: MockerFixture):
    _ = mocker.patch.object(main, "load_config_from_aws", autospec=True, return_value=GENERIC_COURIER_CONFIG)
