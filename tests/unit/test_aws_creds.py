import sys

import pytest
import time_machine

from cloud_courier import aws_credentials
from cloud_courier import path_to_aws_credentials

from .fixtures import mock_path_to_aws_credentials

_fixtures = (mock_path_to_aws_credentials,)


class TestPathToAwsCreds:
    @pytest.mark.skipif(sys.platform != "win32", reason="Only possible to run on Windows")
    def test_Given_system_windows__Then_path_is_windows(self):
        actual = path_to_aws_credentials()

        assert str(actual).startswith("C:")

    @pytest.mark.skipif(sys.platform == "win32", reason="Not possible to run on Windows")
    def test_Given_system_linux__Then_path_is_windows(self):
        actual = path_to_aws_credentials()

        assert str(actual).startswith("/var")


class TestReadAwsCreds:
    @pytest.fixture(autouse=True)
    def _setup(self, mock_path_to_aws_credentials: None):
        pass

    def test_When_read__Then_creds_match_what_is_in_example_file(self):
        actual = aws_credentials.read_aws_creds()

        assert actual["access_key"].startswith("ASIA")
        assert actual["secret_key"].startswith("6spl")
        assert actual["token"].startswith("IQoJ")

    @time_machine.travel("1988-01-19 20:01:02Z")
    def test_When_read__Then_expiry_time_is_25_minutes_in_future(self):
        actual = aws_credentials.read_aws_creds()

        assert actual["expiry_time"] == "1988-01-19T20:26:02Z"
