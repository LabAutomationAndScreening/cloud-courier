import sys

import pytest

from cloud_courier import path_to_aws_credentials


class TestPathToAwsCreds:
    @pytest.mark.skipif(sys.platform != "win32", reason="Only possible to run on Windows")
    def test_Given_system_windows__Then_path_is_windows(self):
        actual = path_to_aws_credentials()

        assert str(actual).startswith("C:")

    @pytest.mark.skipif(sys.platform == "win32", reason="Not possible to run on Windows")
    def test_Given_system_linux__Then_path_is_windows(self):
        actual = path_to_aws_credentials()

        assert str(actual).startswith("/var")
