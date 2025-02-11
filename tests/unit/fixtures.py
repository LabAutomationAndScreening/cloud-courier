from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cloud_courier import aws_credentials

PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS = Path(__file__).parent.resolve() / "example_windows_aws_creds.ini"


@pytest.fixture
def mock_path_to_aws_credentials(mocker: MockerFixture):
    _ = mocker.patch.object(
        aws_credentials, "path_to_aws_credentials", autospec=True, return_value=PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS
    )
