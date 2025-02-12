import uuid

import boto3
import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from cloud_courier import extract_role_name_from_arn
from cloud_courier import load_config
from cloud_courier import load_config_from_aws

from .fixtures import GENERIC_COURIER_CONFIG
from .fixtures import cleanup_config_in_aws
from .fixtures import store_config_in_aws


@pytest.mark.parametrize(
    ("arn", "expected"),
    [
        pytest.param(
            "arn:aws:sts::423623810054:assumed-role/cambridge--cytation-5--cloud-courier--dev/mi-085b6ad72febfabf4",
            "cambridge--cytation-5--cloud-courier--dev",
            id="windows managed instance",
        ),
        pytest.param(
            "arn:aws:sts::423623840054:assumed-role/cambridge--cytation-5--cloud-courier--dev",
            "cambridge--cytation-5--cloud-courier--dev",
            id="no managed instance",
        ),
    ],
)
def test_extract_role_name_from_arn(arn: str, expected: str):
    actual = extract_role_name_from_arn(arn)

    assert actual == expected


class TestLoadConfigFromAws:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        store_config_in_aws(GENERIC_COURIER_CONFIG)
        self.session = boto3.Session(region_name=GENERIC_COURIER_CONFIG.aws_region)
        _ = mocker.patch.object(
            load_config,
            "get_role_arn",
            autospec=True,
            return_value=f"arn:aws:sts::423123810054:assumed-role/{GENERIC_COURIER_CONFIG.role_name}/mi-085b6ad72febfabf4",
        )
        yield
        cleanup_config_in_aws(GENERIC_COURIER_CONFIG)

    def test_single_folder(self):
        actual = load_config_from_aws(self.session)

        assert actual.folders_to_watch == GENERIC_COURIER_CONFIG.folders_to_watch

    def test_Given_malformed_folder_value__Then_log_contains_folder_descriptor(self, mocker: MockerFixture):
        spied_logger_exception = mocker.spy(load_config.logger, "exception")
        expected_descriptor = "fcs-files"
        ssm_client = self.session.client("ssm")
        value = str(uuid.uuid4())
        _ = ssm_client.put_parameter(
            Name=f"/cloud-courier/{GENERIC_COURIER_CONFIG.alias_name}/folders/{expected_descriptor}",
            Value=value,
            Type="String",
            Overwrite=True,
        )

        with pytest.raises(ValidationError, match=value):
            _ = load_config_from_aws(self.session)

        spied_logger_exception.assert_called_once()
        actual_call = spied_logger_exception.call_args_list[0]
        assert f"for {expected_descriptor}" in actual_call[0][0]
