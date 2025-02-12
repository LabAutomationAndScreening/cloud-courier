from typing import Any

import pytest

from cloud_courier import calculate_aws_checksum

from .fixtures import PATH_TO_EXAMPLE_DATA_FILES


class TestCalculateAwsChecksum:
    @pytest.mark.parametrize(
        ("file_name", "part_size_bytes", "expected"),
        [
            pytest.param("2_bytes.txt", None, "c20ad4d76fe97759aa27a0c99bff6710", id="tiny file done as single upload"),
            pytest.param("50_bytes.txt", 11, "5b3a4ab2248dd6bde45b23ea276736ab-5", id="multiple parts"),
        ],
    )
    def test_calculate_aws_checksum(self, file_name: str, part_size_bytes: None | int, expected: str):
        file_path = PATH_TO_EXAMPLE_DATA_FILES / file_name
        kwargs: dict[str, Any] = {}
        if part_size_bytes is not None:
            kwargs["part_size_bytes"] = part_size_bytes

        actual = calculate_aws_checksum(file_path, **kwargs)

        assert actual == expected
