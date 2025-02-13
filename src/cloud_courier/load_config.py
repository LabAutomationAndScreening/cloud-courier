import logging
from typing import TYPE_CHECKING

import boto3
from mypy_boto3_ssm import SSMClient
from pydantic import BaseModel
from pydantic import ValidationError

from .aws_credentials import get_role_arn
from .courier_config_models import SSM_PARAMETER_PREFIX
from .courier_config_models import SSM_PARAMETER_PREFIX_TO_ALIASES
from .courier_config_models import AppConfig
from .courier_config_models import FolderToWatch

if TYPE_CHECKING:
    from mypy_boto3_ssm.type_defs import ParameterMetadataTypeDef
logger = logging.getLogger(__name__)


def _get_ssm_param_value(ssm_client: SSMClient, name: str) -> str:
    param = ssm_client.get_parameter(Name=name)["Parameter"]
    assert "Value" in param, f"Expected 'Value' in {param}"
    return param["Value"]


def _get_ssm_param_values(ssm_client: SSMClient, prefix: str) -> dict[str, str]:
    parameters: list[ParameterMetadataTypeDef] = []
    next_token = None

    while True:
        # API call with optional pagination
        response = ssm_client.describe_parameters(
            ParameterFilters=[{"Key": "Name", "Option": "BeginsWith", "Values": [prefix]}],
            MaxResults=50,  # AWS allows up to 50 results per call
            NextToken=next_token if next_token else "",
        )

        # Add parameters from this page
        parameters.extend(response.get("Parameters", []))

        # Check if more pages exist
        next_token = response.get("NextToken")
        if not next_token:
            break

    params_dict: dict[str, str] = {}
    for param in parameters:
        assert "Name" in param, f"Name not found in parameter {param}"
        param_name = param["Name"]
        param_value = _get_ssm_param_value(
            ssm_client, param_name
        )  # TODO: consider using get_parameters for just a single API call
        folder_descriptor = param_name.split("/")[-1]
        params_dict[folder_descriptor] = param_value

    return params_dict


class CourierConfig(BaseModel, frozen=True):
    folders_to_watch: dict[str, FolderToWatch]
    app_config: AppConfig
    role_name: str
    alias_name: str | None = None
    aws_region: str


def extract_role_name_from_arn(arn: str) -> str:
    assert arn != "arn:aws:iam::000000000000:root", (
        "You are somehow getting the role ARN directly from localstack...you need to mock something in your test."
    )
    return arn.split("/")[1]


def load_config_from_aws(session: boto3.Session) -> CourierConfig:
    ssm_client = session.client("ssm")
    role_name = extract_role_name_from_arn(get_role_arn(session))
    alias = _get_ssm_param_value(ssm_client, f"{SSM_PARAMETER_PREFIX_TO_ALIASES}/{role_name}")
    all_folders = _get_ssm_param_values(ssm_client, f"{SSM_PARAMETER_PREFIX}/{alias}/folders/")
    folders_to_watch: dict[str, FolderToWatch] = {}
    for folder_descriptor, folder_info in all_folders.items():
        try:
            folder_model = FolderToWatch.model_validate_json(folder_info)
        except ValidationError:
            logger.exception(f"Failed to validate folder info for {folder_descriptor}")
            raise
        folders_to_watch[folder_descriptor] = folder_model

    return CourierConfig(
        folders_to_watch=folders_to_watch,
        app_config=AppConfig(),
        role_name=role_name,
        alias_name=alias,
        aws_region=session.region_name,
    )
