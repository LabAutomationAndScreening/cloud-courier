from pydantic import BaseModel

from .courier_config_models import AppConfig
from .courier_config_models import FolderToWatch


class CourierConfig(BaseModel, frozen=True):
    folders_to_watch: tuple[FolderToWatch, ...]
    app_config: AppConfig


def extract_role_name_from_arn(arn: str) -> str:
    return arn.split("/")[-1]


def load_config_from_aws() -> None:
    pass
