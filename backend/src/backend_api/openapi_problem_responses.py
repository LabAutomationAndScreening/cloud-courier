# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any
from typing import NamedTuple

from .fast_api_exception_handlers import ProblemDetails

PROBLEM_DETAILS_REF = "#/components/schemas/ProblemDetails"
PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


class ProblemExample(NamedTuple):
    """One named alternative for a status code that several distinct failures can produce.

    Carries only the parts that vary between them; the surrounding ``ProblemDetails`` envelope is filled
    in by :func:`problem_response` so every example stays a valid instance of the schema it sits under.
    """

    summary: str
    detail: str


def _problem_body(*, status_code: int, detail: str, instance: str) -> dict[str, Any]:  # pyrefly: ignore[explicit-any] # model_dump returns dict[str, Any]; see the note on problem_response's return type
    return ProblemDetails(
        title=HTTPStatus(status_code).phrase, status=status_code, detail=detail, instance=instance
    ).model_dump(mode="json", by_alias=True)


def problem_response(
    status_code: int,
    description: str,
    *,
    instance: str = "about:blank",
    examples: Mapping[str, ProblemExample] | None = None,
) -> dict[int | str, dict[str, Any]]:  # pyrefly: ignore[explicit-any] # OpenAPI response fragments are heterogeneous nested JSON; JsonValue would force every consumer to narrow through the union to reach a leaf
    """Build an OpenAPI ``responses`` entry documenting a ``ProblemDetails`` error.

    Holds the ~80% that every error response shares (the ``application/problem+json`` media type and the
    ``ProblemDetails`` schema ref) so route decorators only pass what differs: status and description.
    Merge several with dict unpacking: ``{**problem_response(...), **problem_response(...)}``.

    ``example`` is synthesized from ``status_code`` and ``description`` so the docs
    show a body that matches this response (e.g. a 400 titled "Bad Request") instead of the generic
    field-level example rendered from a bare ``ProblemDetails`` schema ref. Pass ``instance`` to point the
    example at the route's real path.

    When one status code covers several distinct failures, pass ``examples`` instead: each
    :class:`ProblemExample` becomes a named entry, expanded here into a full ``ProblemDetails`` body.
    Expanding them here rather than at the call site is what keeps them valid against the schema they sit
    under — a hand-written ``{"detail": ...}`` omits the required ``title``, ``status`` and ``instance``.
    """
    content: dict[str, Any] = {"schema": {"$ref": PROBLEM_DETAILS_REF}}  # pyrefly: ignore[explicit-any] # matches the return type above
    if examples is None:
        content["example"] = _problem_body(status_code=status_code, detail=description, instance=instance)
    else:
        named_examples: dict[str, Any] = {}  # pyrefly: ignore[explicit-any] # matches the return type above
        for name, example in examples.items():
            named_examples[name] = {
                "summary": example.summary,
                "value": _problem_body(status_code=status_code, detail=example.detail, instance=instance),
            }
        content["examples"] = named_examples
    return {status_code: {"description": description, "content": {PROBLEM_JSON_MEDIA_TYPE: content}}}
