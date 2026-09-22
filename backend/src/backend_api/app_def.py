# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import asyncio
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import override

from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_offline import FastAPIOffline
from pydantic import Field

from .camel_case_model import CamelCaseModel
from .entrypoint.parser import get_version
from .fast_api_exception_handlers import register_exception_handlers
from .jinja_constants import HUMAN_FRIENDLY_APP_NAME
from .main import start_courier

logger = logging.getLogger(__name__)
# how long to wait for the upload agent to finish its current work once it has been told to stop. Kept well
# inside the 30s grace period SvcStop allows before the service control manager force-terminates the process.
COURIER_SHUTDOWN_TIMEOUT_SECONDS = 20
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
API_DESCRIPTION = "Agent to upload files to cloud"

OPENAPI_APP_SPECIFIC_TAGS: list[dict[str, str]] = [
    # Insert app specific openapi tags here
]

OPENAPI_TAGS = [
    {"name": "system", "description": "Server health and lifecycle operations."},
    *OPENAPI_APP_SPECIFIC_TAGS,
]


def _start_courier_thread(app: FastAPI) -> threading.Thread | None:
    try:
        cli_args = app.state.courier_args
        stop_event = app.state.stop_event
    except AttributeError:
        # the app is being served without going through the entrypoint, as in the unit tests that build a
        # TestClient or a `uvicorn src.entrypoint:app --reload` dev session. There are no CLI arguments to
        # run the agent with, so serve the API alone rather than guessing at an AWS region or a watch folder.
        logger.info("No CLI arguments found on the app state, so the upload agent will not be started")
        return None
    if cli_args.skip_upload_agent:
        logger.info("Serving the API without the upload agent, because --skip-upload-agent was passed")
        return None

    def run_courier() -> None:
        try:
            _ = start_courier(cli_args, stop_event=stop_event)
        except Exception:
            logger.exception("The upload agent stopped because of an unhandled exception")
            app.state.courier_failed = True
        finally:
            # whatever stopped the agent, stop the server with it. A process serving healthchecks while
            # silently uploading nothing looks identical to a working one.
            stop_event.set()

    thread = threading.Thread(target=run_courier, name="cloud-courier-agent", daemon=True)
    thread.start()
    return thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    courier_thread = _start_courier_thread(app)
    try:
        yield
    finally:
        if courier_thread is not None:
            app.state.stop_event.set()
            await asyncio.to_thread(courier_thread.join, COURIER_SHUTDOWN_TIMEOUT_SECONDS)
            if courier_thread.is_alive():
                logger.error(
                    f"The upload agent did not stop within {COURIER_SHUTDOWN_TIMEOUT_SECONDS}s; "
                    "an upload may have been interrupted"
                )


try:
    app = FastAPIOffline(
        lifespan=lifespan,
        title=HUMAN_FRIENDLY_APP_NAME,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        favicon_url="favicon.ico",
        version=get_version(),
        docs_url="/api-docs",
        openapi_url="/api/openapi.json",
        static_url="/static/swagger",
    )
except (  # pragma: no cover # This is just logging unexpected errors, and it's very challenging to explicitly unit test
    Exception
):
    logger.exception("Unhandled error instantiating FastAPI object")
    raise


class HealthcheckResponse(CamelCaseModel):
    """Result of an API health check.

    Reports the running application version so a caller can confirm the server is up and identify which
    build is currently deployed.
    """

    version: str = Field(description="Version of the application", default="1.0.0", examples=["1.0.0"])


class HealthcheckQuery(CamelCaseModel):
    prepend_v: bool = Field(default=False, description="Include a 'v' before the version number")


class ShutdownResponse(CamelCaseModel):
    """Acknowledgement of a server shutdown request.

    Returned immediately when a shutdown is requested; the server process exits shortly after this response
    is sent.
    """

    message: str = Field(
        default="Shutdown request received. Server will exit shortly.",
        description="Message indicating the shutdown request was received",
        examples=["Shutdown request received. Server will exit shortly."],
    )


class NoCacheStaticFiles(StaticFiles):
    """Set cache control headers to prevent caching."""

    @override
    def file_response(  # pragma: no cover # This generally just gets hit by E2E tests
        self,
        *args: Any,  # pyrefly: ignore[explicit-any] # must match the signature of the Starlette method being overridden; https://github.com/facebook/pyrefly/issues/4548 tracks exempting @override methods
        **kwargs: Any,  # pyrefly: ignore[explicit-any] # must match the signature of the Starlette method being overridden; https://github.com/facebook/pyrefly/issues/4548 tracks exempting @override methods
    ) -> Any:  # pyrefly: ignore[explicit-any] # must match the signature of the Starlette method being overridden; https://github.com/facebook/pyrefly/issues/4548 tracks exempting @override methods
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@app.get("/api/healthcheck", summary="Check API health", tags=["system"])
def healthcheck(
    query: Annotated[HealthcheckQuery, Query()],
) -> HealthcheckResponse:
    return HealthcheckResponse(version=get_version(prepend_v=query.prepend_v))


@app.get("/api/shutdown", summary="Shut down the server", tags=["system"])
def shutdown() -> ShutdownResponse:
    logger.info("Server shutdown request received")

    def do_shutdown():
        time.sleep(0.1)  # Give time for the request to return a success response
        logger.info("Server is shutting down.")
        os._exit(
            0
        )  # sys.exit just causes an internal server error, it doesn't actually stop the server. So a hard exit is needed

    threading.Thread(target=do_shutdown, name="execute_shutdown").start()
    return ShutdownResponse()


try:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Super permissive CORS setting since this is for intranet
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )
    app.mount(
        "/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static"
    )  # this needs to go after any defined routes so that the routes take precedence
    register_exception_handlers(app)
except (  # pragma: no cover # This is just logging unexpected errors, and it's very challenging to explicitly unit test
    Exception
):
    logger.exception("Unhandled error")
    raise
