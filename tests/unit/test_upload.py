import tempfile
import uuid
from pathlib import Path

import boto3
import pytest
from pytest_mock import MockerFixture

from cloud_courier import MIN_MULTIPART_BYTES
from cloud_courier import ChecksumMismatchError
from cloud_courier import upload
from cloud_courier import upload_to_s3

from .fixtures import PATH_TO_EXAMPLE_DATA_FILES


class TestUploadToS3:
    @pytest.fixture(
        autouse=True
    )  # TODO: figure out why everything fails if this is set to a class or module-scoped function
    def _s3_bucket(self):
        self.aws_region = "us-east-1"
        self.bucket_name = str(uuid.uuid4())
        self.boto_session = boto3.Session(region_name=self.aws_region)
        s3_client = self.boto_session.client("s3")
        _ = s3_client.create_bucket(Bucket=self.bucket_name)
        yield
        s3 = boto3.resource("s3", region_name=self.aws_region)
        bucket = s3.Bucket(self.bucket_name)
        _ = bucket.objects.all().delete()
        _ = s3_client.delete_bucket(Bucket=self.bucket_name)

    @pytest.mark.parametrize(
        ("file_name"),
        [
            pytest.param("3_bytes.txt", id="tiny file"),
            pytest.param("50_bytes.txt", id="slightly larger file"),
        ],
    )
    def test_upload_to_s3(self, file_name: str):
        object_key = str(uuid.uuid4())

        _ = upload_to_s3(
            file_path=PATH_TO_EXAMPLE_DATA_FILES / file_name,
            boto_session=self.boto_session,
            bucket_name=self.bucket_name,
            object_key=object_key,
        )

    def test_Given_mocked_checksum_mismatch__Then_error(self, mocker: MockerFixture):
        local_checksum = str(uuid.uuid4())
        _ = mocker.patch.object(upload, "calculate_aws_checksum", autospec=True, return_value=local_checksum)

        with pytest.raises(ChecksumMismatchError, match=local_checksum):
            _ = upload_to_s3(
                file_path=PATH_TO_EXAMPLE_DATA_FILES / "3_bytes.txt",
                boto_session=self.boto_session,
                bucket_name=self.bucket_name,
                object_key=str(uuid.uuid4()),
            )

    @pytest.mark.parametrize(
        ("num_bytes", "expected_checksum"),
        [
            pytest.param(
                MIN_MULTIPART_BYTES + 1, "67506b303063b67eba300fd2f937661b-2", id="above multi-part threshold"
            ),
            pytest.param(
                MIN_MULTIPART_BYTES, "7d7a6dd7e37454c6a82992eabe7a4613", id="when at thresheld, then single-part"
            ),
        ],
    )
    def test_large_files(self, num_bytes: int, expected_checksum: str):
        with tempfile.NamedTemporaryFile() as f:
            _ = f.write(b"0" * num_bytes)
            f.flush()

            actual_checksum = upload_to_s3(
                file_path=Path(f.name),
                boto_session=self.boto_session,
                bucket_name=self.bucket_name,
                object_key=str(uuid.uuid4()),
            )

        assert actual_checksum == expected_checksum
