import random
from unittest.mock import ANY

import pytest
from botocore.session import Session
from pytest_mock import MockerFixture

from cloud_courier import main

from .fixtures import mock_path_to_aws_credentials

_fixtures = (mock_path_to_aws_credentials,)


def test_Given_no_args__When_run__Then_returns_error_code():
    # TODO: capture the log message so the stderr is not overrun with log messages during testing
    assert main([]) > 0


class TestArgParse:
    @pytest.fixture(autouse=True)
    def _setup(self, mock_path_to_aws_credentials: None):
        pass

    def test_When_run__Then_AWS_region_passed_to_boto(self, mocker: MockerFixture):
        spied_set_config = mocker.spy(Session, "set_config_variable")
        expected_region = random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"])

        assert main(["--immediate-shut-down", "--aws-region", expected_region]) == 0

        spied_set_config.assert_called_once_with(ANY, "region", expected_region)
