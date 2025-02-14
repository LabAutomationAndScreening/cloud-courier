from pathlib import Path

from cloud_courier import AppConfig
from cloud_courier import CourierConfig
from cloud_courier import FolderToWatch

PATH_TO_EXAMPLE_DATA_FILES = Path(__file__).parent.resolve() / "example_data_files"
PATH_TO_EXAMPLE_WINDOWS_AWS_CREDS = Path(__file__).parent.resolve() / "example_windows_aws_creds.ini"

GENERIC_COURIER_CONFIG = CourierConfig(
    role_name="cambridge--cytation-5--cloud-courier--prod",
    alias_name="woburn--cytation-5--prod",
    app_config=AppConfig(),
    folders_to_watch={
        "fcs-files": FolderToWatch(
            folder_path=str(Path("/tmp")),  # noqa: S108 # this is not insecure to have the generic temp folder
            s3_key_prefix="woburn/cytation-5",
            s3_bucket_name="my-bucket",
            delay_seconds_before_upload=0.05,
        )
    },
    aws_region="us-east-1",
)

COMPLEX_COURIER_CONFIG = CourierConfig(
    role_name="emeryville--star-1--cloud-courier--prod",
    app_config=AppConfig(),
    folders_to_watch={
        str(x): FolderToWatch(
            folder_path=str(x),
            s3_key_prefix="emeryville/star-1",
            s3_bucket_name="my-bucket",
            delay_seconds_before_upload=0.05,
        )
        for x in range(100)
    },
    aws_region="us-west-1",
)
