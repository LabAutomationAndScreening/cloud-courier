import datetime
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import boto3

from .courier_config_models import FolderToWatch

if TYPE_CHECKING:
    from mypy_boto3_s3.type_defs import CompletedPartTypeDef

logger = logging.getLogger(__name__)

MIN_MULTIPART_BYTES = 5 * 1024 * 1024


class ChecksumMismatchError(Exception):
    def __init__(self, local_checksum: str, s3_checksum: str):
        super().__init__(f"Checksum mismatch! Locally calculated: {local_checksum}, S3: {s3_checksum}")


def _get_part_size(file_path: Path, part_size_bytes: int = MIN_MULTIPART_BYTES) -> tuple[bool, int]:
    file_size = file_path.stat().st_size
    if file_size <= part_size_bytes:
        return False, file_size
    return True, part_size_bytes


def convert_path_to_s3_object_key(file_path: str, folder_config: FolderToWatch) -> str:
    # cannot accept a Path object here because trying to test windows paths on linux fails
    # TODO: handle more invalid characters https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
    file_path = file_path.replace(":", "")
    file_path = file_path.replace("\\", "/")
    file_path = file_path.replace(" ", "_")
    file_path = file_path.removeprefix("/")
    return f"{folder_config.s3_key_prefix}/{file_path}"


def convert_path_to_s3_object_tag(file_path: str) -> str:
    # https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-tagging.html
    return file_path.replace(":", "").replace("\\", "/")[-256:]


def calculate_aws_checksum(file_path: Path, part_size_bytes: int = MIN_MULTIPART_BYTES) -> str:
    is_multi_part, part_size_bytes = _get_part_size(file_path, part_size_bytes)
    md5_list: list[bytes] = []

    # Read the file in chunks and calculate MD5 for each part
    with file_path.open("rb") as f:
        while chunk := f.read(part_size_bytes):
            md5_hash = hashlib.md5(chunk)  # noqa: S324 # we don't need this to be secure, this is just a checksum for file integrity
            md5_list.append(md5_hash.digest())

    if is_multi_part:
        # Combine the part MD5s and compute the final ETag
        combined_md5 = hashlib.md5(b"".join(md5_list)).hexdigest()  # noqa: S324 # we don't need this to be secure, this is just a checksum for file integrity
        part_count = len(md5_list)
        # Return the ETag in the format "<combined-hash>-<part-count>"
        return f"{combined_md5}-{part_count}"
    return md5_list[0].hex()


def dummy_function_during_multipart_upload():
    """Do nothing.

    This function is used to be able to mock an error occurring during upload.
    """


def upload_to_s3(
    *,
    file_path: Path,
    boto_session: boto3.Session,
    bucket_name: str,
    object_key: str,
) -> str:
    checksum = calculate_aws_checksum(file_path)
    s3_client = boto_session.client("s3")
    is_multi_part, part_size_bytes = _get_part_size(file_path)
    file_size = file_path.stat().st_size
    logger.info(
        f"Starting {'multi-' if is_multi_part else 'single '}part upload for '{file_path}' ({file_size} bytes) with part size {part_size_bytes} bytes. Destination: s3://{bucket_name}/{object_key}"
    )
    if is_multi_part:
        response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_key)
        upload_id = response["UploadId"]
        parts: list[CompletedPartTypeDef] = []

        try:
            with file_path.open("rb") as f:
                part_number = 1
                while True:
                    data = f.read(part_size_bytes)
                    if not data:
                        break  # End of file reached
                    logger.info(f"Uploading part {part_number}...")

                    part_response = s3_client.upload_part(
                        Bucket=bucket_name, Key=object_key, PartNumber=part_number, UploadId=upload_id, Body=data
                    )
                    parts.append({"ETag": part_response["ETag"], "PartNumber": part_number})
                    part_number += 1
                    dummy_function_during_multipart_upload()

            logger.info("Completing multipart upload...")
            _ = s3_client.complete_multipart_upload(
                Bucket=bucket_name, Key=object_key, UploadId=upload_id, MultipartUpload={"Parts": parts}
            )

        except Exception:
            logger.exception("An error occurred, aborting multipart upload.")
            _ = s3_client.abort_multipart_upload(Bucket=bucket_name, Key=object_key, UploadId=upload_id)
            raise
    else:
        # Single part upload
        with file_path.open("rb") as f:
            s3_client.upload_fileobj(f, bucket_name, object_key)
    file_stats = file_path.stat()
    last_modified_time = datetime.datetime.fromtimestamp(file_stats.st_mtime, tz=datetime.UTC).isoformat()
    # Creation time on Windows (st_ctime). On Linux, this is metadata change time.
    creation_time = datetime.datetime.fromtimestamp(file_stats.st_ctime, tz=datetime.UTC).isoformat()
    # TODO: add custom tags specified by the config
    # TODO: catch client error and log the attempted tag keys/values for easier troubleshooting---botocore.exceptions.ClientError: An error occurred (InvalidTag) when calling the PutObjectTagging operation: The TagValue you have provided is invalid
    _ = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=object_key,
        Tagging={
            "TagSet": [
                {"Key": "uploaded-by", "Value": "cloud-courier"},
                {"Key": "original-file-path", "Value": convert_path_to_s3_object_tag(str(file_path))},
                {"Key": "file-last-modified-at", "Value": last_modified_time},
                {"Key": "file-created-at", "Value": creation_time},
            ]
        },
    )

    s3_etag = s3_client.head_object(Bucket=bucket_name, Key=object_key)["ETag"].strip('"')
    if s3_etag != checksum:
        raise ChecksumMismatchError(checksum, s3_etag)
    logger.info("Upload completed successfully!")
    return checksum
