from pydantic import BaseModel
from pydantic import Field

SSM_PARAMETER_PREFIX = "/cloud-courier"
SSM_PARAMETER_PREFIX_TO_ALIASES = f"{SSM_PARAMETER_PREFIX}/computer-aliases"


class FolderToWatch(BaseModel, frozen=True):
    config_format_version: str = "1.0"
    folder_path: str
    recursive: bool = True
    file_pattern: str = "*"  # TODO: implement
    ignore_patterns: list[str] = Field(default_factory=list)  # TODO: implement
    s3_key_prefix: str
    s3_bucket_name: str
    # TODO: allow truncating part of the file path prefix
    # TODO: allow deleting after upload
    # TODO: allow specifying a wait period before upload.
    # TODO: add dict of extra key/value pairs to add as metadata to the S3 object (e.g. instrument serial number)
    # TODO: add a bool if you expect files to change and want to always fully calculate checksums even if the file path itself has already been uploaded (can substantially slow down startup time if lots of large files in the folder)


# TODO: check the whole list of folders to watch and confirm there's no overlaps


# Future AppConfig level settings:
# TODO: add time windows where upload/monitoring should be fully paused (e.g. only upload on weekends or at night)

# TODO: add the ability to check that CPU usage has been sufficiently low the past X hours before beginning upload (concerns about an overnight run having been started, even when upload is normally restricted to night time only)

# TODO: (maybe just infra-side) add heartbeat alert time window. add times when not to check for heartbeats (e.g. if computer is regularly turned off at night or weekends)


class AppConfig(BaseModel, frozen=True):
    config_format_version: str = "1.0"
    config_refresh_frequency_minutes: int = 60
