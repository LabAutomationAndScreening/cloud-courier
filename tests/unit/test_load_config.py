import boto3
import pytest
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
