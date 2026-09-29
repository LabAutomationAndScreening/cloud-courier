# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from pydantic.fields import ComputedFieldInfo
from pydantic.fields import FieldInfo


def _title_from_field_name(field_name: str, _info: FieldInfo | ComputedFieldInfo) -> str:  # noqa: ARG001  # signature fixed by pydantic field_title_generator
    """Generate the JSON-schema ``title`` from the snake_case field name.

    Without this, pydantic derives ``title`` from the camelCase alias (``remoteUrl`` -> "Remoteurl").
    Titleizing the python field name restores the pre-camelize output ("Remote Url"), which the
    frontend code generator relies on.
    """
    return field_name.replace("_", " ").title()


class CamelCaseModel(BaseModel):
    """Base for schema models that serialize field names as camelCase over the wire."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        field_title_generator=_title_from_field_name,
    )
