import uuid

import boto3
import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from cloud_courier import extract_role_name_from_arn
from cloud_courier import load_config
from cloud_courier import load_config_from_aws

from .constants import COMPLEX_COURIER_CONFIG
from .constants import GENERIC_COURIER_CONFIG
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


class TestWhenSsmReturnsAnEmptyNextToken:
    def test_Given_single_page_response__When_ssm_params_fetched__Then_only_one_request_made_and_it_omits_next_token(
        self, mocker: MockerFixture
    ):
        prefix = f"/{uuid.uuid4()}"
        folder_descriptor = str(uuid.uuid4())
        param_value = str(uuid.uuid4())
        ssm_client = boto3.Session(region_name=GENERIC_COURIER_CONFIG.aws_region).client("ssm")
        mocked_describe = mocker.patch.object(
            ssm_client,
            ssm_client.describe_parameters.__name__,
            side_effect=[{"Parameters": [{"Name": f"{prefix}/{folder_descriptor}"}], "NextToken": ""}],
        )
        _ = mocker.patch.object(
            ssm_client, ssm_client.get_parameter.__name__, return_value={"Parameter": {"Value": param_value}}
        )

        actual = load_config._get_ssm_param_values(ssm_client, prefix)  # noqa: SLF001 # the pagination behavior under test is only reachable through this private helper

        assert actual == {folder_descriptor: param_value}
        mocked_describe.assert_called_once_with(
            ParameterFilters=[{"Key": "Name", "Option": "BeginsWith", "Values": [prefix]}], MaxResults=50
        )


class LoadConfigFromAws:
    _config = GENERIC_COURIER_CONFIG

    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        store_config_in_aws(self._config)
        self.session = boto3.Session(region_name=self._config.aws_region)
        _ = mocker.patch.object(
            load_config,
            "get_role_arn",
            autospec=True,
            return_value=f"arn:aws:sts::423123810054:assumed-role/{self._config.role_name}/mi-085b6ad72febfabf4",
        )
        yield
        cleanup_config_in_aws(self._config)


class TestLoadGenericConfigFromAws(LoadConfigFromAws):
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


class TestLoadComplexConfigFromAws(LoadConfigFromAws):
    _config = COMPLEX_COURIER_CONFIG

    def test_more_folders_than_ssm_get_parameters_pagination_size(self):
        actual = load_config_from_aws(self.session)
        arbitrary_min_expected_num_folders = 50

        assert len(actual.folders_to_watch) > arbitrary_min_expected_num_folders
        assert actual.folders_to_watch == COMPLEX_COURIER_CONFIG.folders_to_watch
