from pydantic import BaseModel
from pydantic import Field


class FolderToWatch(BaseModel, frozen=True):
    folder_path: str
    recursive: bool = True
    file_pattern: str = "*"
    ignore_patterns: list[str] = Field(default_factory=list)
    s3_key_prefix: str
    s3_bucket_name: str
    # TODO: allow truncating part of the file path prefix
    # TODO: allow deleting after upload
    # TODO: allow specifying a wait period before upload
    # TODO: add dict of extra key/value pairs to add as metadata to the S3 object (e.g. instrument serial number)


# TODO: check the whole list of folders to watch and confirm there's no overlaps


# Future AppConfig level settings:
# TODO: add time windows where upload/monitoring should be fully paused (e.g. only upload on weekends or at night)

# TODO: add the ability to check that CPU usage has been sufficiently low the past X hours before beginning upload (concerns about an overnight run having been started, even when upload is normally restricted to night time only)


class AppConfig(BaseModel, frozen=True):
    config_refresh_frequency_minutes: int = 60


class CourierConfig(BaseModel, frozen=True):
    folders_to_watch: tuple[FolderToWatch, ...]
    app_config: AppConfig
