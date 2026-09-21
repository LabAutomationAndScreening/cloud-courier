# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import json
import logging
from functools import partial
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import Field
from pydantic import JsonValue
from starlette.exceptions import HTTPException
from uuid_utils import uuid7

from .camel_case_model import CamelCaseModel
from .openapi_schema_simplifier import collapse_nullable_anyof

logger = logging.getLogger(__name__)


_HTTP_STATUS_SCHEMA: dict[str, JsonValue] = {"format": "int32", "minimum": 100, "maximum": 599}


class ProblemDetails(CamelCaseModel):
    """RFC 9457 problem details describing an error response.

    Returned (as application/problem+json) for error responses so clients and codegen tools such as Kiota
    have a consistent, machine-readable error shape.
    """

    type: str = Field(
        default="about:blank", examples=["about:blank"], description="A URI reference identifying the problem type."
    )
    title: str = Field(
        examples=["Internal Server Error"], description="A short, human-readable summary of the problem."
    )
    status: int = Field(
        json_schema_extra=_HTTP_STATUS_SCHEMA, examples=[500], description="The HTTP status code for this problem."
    )
    # The vendor extension lets Kiota use this as the exception message.
    detail: str = Field(
        ...,
        json_schema_extra={"x-ms-primary-error-message": True},
        examples=["An unexpected error occurred."],
        description="A human-readable explanation specific to this occurrence of the problem.",
    )
    instance: str = Field(examples=["/api/healthcheck"], description="A URI reference identifying this occurrence.")
    error_type: str | None = Field(
        default=None,
        examples=["ValueError"],
        description="The internal exception class name, when available.",
    )


def should_show_error_details() -> bool:
    return True  # pragma: no cover # TODO: implement and test the ability to specify via config, CLI, and envvar whether to show error details, and set the default to False


def _short(msg: str, max_len: int = 2000) -> str:
    return msg if len(msg) <= max_len else msg[:max_len] + "...(truncated)"


def _problem_dict(
    *,
    title: str,
    status: int,
    detail: str,
    trace_id: str,
    exc_type: str,
) -> dict[str, JsonValue]:
    return ProblemDetails(
        type="about:blank",
        title=title,
        status=status,
        detail=detail,
        instance=f"urn:uuid:{trace_id}",
        error_type=exc_type,
    ).model_dump(by_alias=True, mode="json")


class ExceptionHandler:
    def __init__(self, app: FastAPI):
        super().__init__()
        self._app = app
        generator: CORSMiddleware | None = None
        for m in app.user_middleware:
            assert isinstance(m.cls, type), f"Expected middleware class to be a type, got {type(m.cls)}"
            if issubclass(m.cls, CORSMiddleware):
                generator = CORSMiddleware(
                    app,
                    **m.kwargs,  # pyrefly: ignore[bad-argument-type] # pyrefly doesn't like kwargs, but we're just passing them through to Starlette
                )
            else:
                continue  # pragma: no cover # not worth testing a longer list right now

        if generator is None:
            raise NotImplementedError("CORS Middleware not found, cannot set CORS headers on exception responses")

        # TODO: consider if more dynamic headers would need to be used for some complex CORS setups
        self._cors_headers = generator.simple_headers

    def handle_http_exception(self, request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, HTTPException), f"Expected HTTPException, got {type(exc)}"
        error_trace_id = uuid7()
        logger.warning(
            f"{exc.__class__.__name__} on {request.method} {request.url.path} [urn:uuid:{error_trace_id}]",
            exc_info=exc,
        )
        # starlette annotates HTTPException.detail as str, but FastAPI's subclass widens it to Any, so a route
        # can raise one carrying a dict or list. RFC 9457 requires detail to be a string, and json.dumps keeps
        # such a payload readable as JSON rather than rendering it as a Python repr.
        if isinstance(exc.detail, str):
            detail = exc.detail
        else:
            detail = json.dumps(exc.detail)
        body = _problem_dict(
            title="HTTP Error",
            status=exc.status_code,
            detail=detail,
            trace_id=str(error_trace_id),
            exc_type=exc.__class__.__name__,
        )
        return self._json_response(status_code=exc.status_code, body=body)

    def register(self):
        self._app.add_exception_handler(HTTPException, self.handle_http_exception)
        self._app.add_exception_handler(RequestValidationError, self.handle_validation_exception)
        self._app.add_exception_handler(Exception, self.handle_unhandled_exception)

    def _json_response(self, *, status_code: int, body: dict[str, JsonValue]) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content=body,
            media_type="application/problem+json",
            headers=self._cors_headers,
        )

    def handle_validation_exception(self, request: Request, exc: Exception) -> JSONResponse:
        error_trace_id = uuid7()
        logger.warning(
            f"{exc.__class__.__name__} on {request.method} {request.url.path} [urn:uuid:{error_trace_id}]", exc_info=exc
        )
        body = _problem_dict(
            title="Validation Error",
            status=422,
            detail=_short(str(exc)),
            trace_id=str(error_trace_id),
            exc_type=exc.__class__.__name__,
        )
        return self._json_response(status_code=422, body=body)

    def handle_unhandled_exception(self, request: Request, exc: Exception) -> JSONResponse:
        error_trace_id = uuid7()
        logger.error(
            f"Unhandled {exc.__class__.__name__} on {request.method} {request.url.path} [urn:uuid:{error_trace_id}]",
            exc_info=exc,
        )

        msg = _short(str(exc)) if should_show_error_details() else "An unexpected error occurred."
        body = _problem_dict(
            title="Internal Server Error",
            status=500,
            detail=msg,
            trace_id=str(error_trace_id),
            exc_type=exc.__class__.__name__,
        )
        return self._json_response(status_code=500, body=body)


def custom_openapi(app: FastAPI) -> dict[str, Any]:  # pyrefly: ignore[explicit-any] # this wraps FastAPI's get_openapi(), which is annotated as returning dict[str, Any]
    """Modify the OpenAPI schema to be more explicit about the generic errors that any route can throw.

    This helps with codegen tools such as Kiota.
    """
    if app.openapi_schema is not None:  # don't regenerate the schema on subsequent API calls if it's already been done
        return app.openapi_schema
    oas = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
        tags=app.openapi_tags,
        servers=app.servers,
    )

    # Ensure ProblemDetails schema exists
    # get_openapi() is annotated as returning dict[str, Any], so every value walked out of it is an implicit
    # Any. These annotations state the shape the OpenAPI spec guarantees, which is the only way to keep the
    # rest of this function type-checked.
    comps: dict[str, dict[str, JsonValue]] = oas.setdefault("components", {}).setdefault("schemas", {})
    _ = comps.setdefault(
        "ProblemDetails",
        ProblemDetails.model_json_schema(ref_template="#/components/schemas/{model}"),
    )

    # FastAPI generates the validation-error schemas without descriptions or examples; we cannot annotate
    # them at the model level, so document and exemplify them here. This also lets every media type that
    # references them (the 422 responses) satisfy the "missing example" lint rule.
    validation_error_example: JsonValue = {
        "loc": ["body", "field_name"],
        "msg": "field required",
        "type": "missing",
    }
    generated_schema_metadata: dict[str, dict[str, JsonValue]] = {
        "HTTPValidationError": {
            "description": "Error response returned when request validation fails.",
            "examples": [{"detail": [validation_error_example]}],
        },
        "ValidationError": {
            "description": "Details of a single request validation failure.",
            "examples": [validation_error_example],
        },
    }
    for schema_name, schema_metadata in generated_schema_metadata.items():
        if (
            schema_name in comps
        ):  # pragma: no branch # every app has at least one validating route (even just the health check), so HTTPValidationError/ValidationError are always already in comps by the time this runs
            for key, value in schema_metadata.items():
                _ = comps[schema_name].setdefault(key, value)

    def problem_ref() -> dict[str, JsonValue]:
        return {"$ref": "#/components/schemas/ProblemDetails"}

    def problem_content() -> dict[str, JsonValue]:
        return {"application/problem+json": {"schema": problem_ref()}}

    # annotated for the same reason as `comps` above; from here on the walk is checked against the shape the
    # OpenAPI spec guarantees: paths map to operations, and an operation maps keys to JSON values
    paths: dict[str, dict[str, dict[str, JsonValue]]] = oas.get("paths", {})
    for methods in paths.values():
        for method, op in list(methods.items()):
            if method not in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
                continue  # pragma: no cover # Most schemas we create will only have those types of methods, so this line will never be hit.  But there are others that are possible (it seems), such as summary/description/servers
            assert "responses" in op, (
                f"Expected FastAPI to have generated a responses object for the {method} operation"
            )
            responses = op["responses"]
            assert isinstance(responses, dict), f"Expected the responses object to be a dict, got {type(responses)}"

            # Do NOT touch 422 if FastAPI added it, only add additional responses:
            # 500 should never be present in any defined route, so always add it
            _ = responses.setdefault(
                "500",
                {
                    "description": "Internal Server Error",
                    "content": problem_content(),
                },
            )

            # Optional but recommended for Kiota: add default catch-all.  'default' should never be present in a route, so no need to check for it before adding it
            _ = responses.setdefault(
                "default",
                {
                    "description": "Error",
                    "content": problem_content(),
                },
            )

    collapse_nullable_anyof(oas)

    app.openapi_schema = oas
    return oas


def register_exception_handlers(app: FastAPI) -> None:
    handler = ExceptionHandler(app)
    handler.register()
    app.openapi = partial(custom_openapi, app)
