# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import subprocess
from collections.abc import AsyncGenerator
from collections.abc import Generator

import pytest
import pytest_asyncio
from backend_api import configure_logging
from httpx import AsyncClient
from httpx import Limits
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider
from kiota_http.httpx_request_adapter import HttpxRequestAdapter

from .app_bootup import BACKEND_E2E_PORT
from .app_bootup import start_compose
from .app_bootup import start_exe
from .app_bootup import stop_compose
from .app_bootup import stop_exe
from .generated.open_api.backend.backend_client import BackendClient
from .jinja_constants import APPLICATION_BOOTUP_MODE
from .jinja_constants import ApplicationBootupModes


@pytest.fixture(autouse=True, scope="session")
def configure_log():
    configure_logging(log_filename_prefix="logs/pytest-")


@pytest.fixture(autouse=True)
def vcr_config() -> dict[str, object]:
    # disable any network blocking set up for unit tests
    return {"allowed_hosts": ["127.0.0.1", "localhost", "::1"]}


def pytest_configure(config: pytest.Config):
    """Disable coverage reporting for E2E tests."""
    config.pluginmanager.set_blocked("_cov")


def _no_keepalive_limits() -> Limits:
    # Uvicorn closes the HTTP/1.1 connection after a 500 response. Disabling keepalive
    # ensures httpx never reuses a stale socket from a prior failed request.
    return Limits(max_keepalive_connections=0)


@pytest.fixture(scope="session")
def backend_client_session() -> Generator[BackendClient]:
    http_client = AsyncClient(base_url=f"http://localhost:{BACKEND_E2E_PORT}", limits=_no_keepalive_limits())
    try:
        request_adapter = HttpxRequestAdapter(AnonymousAuthenticationProvider(), http_client=http_client)
        yield BackendClient(request_adapter)
    finally:
        _ = http_client.aclose()


@pytest_asyncio.fixture(scope="module")
async def backend_client_module() -> AsyncGenerator[BackendClient]:
    async with AsyncClient(
        base_url=f"http://localhost:{BACKEND_E2E_PORT}", limits=_no_keepalive_limits()
    ) as http_client:
        request_adapter = HttpxRequestAdapter(AnonymousAuthenticationProvider(), http_client=http_client)
        yield BackendClient(request_adapter)


@pytest_asyncio.fixture
async def backend_client() -> AsyncGenerator[BackendClient]:
    async with AsyncClient(
        base_url=f"http://localhost:{BACKEND_E2E_PORT}", limits=_no_keepalive_limits()
    ) as http_client:
        request_adapter = HttpxRequestAdapter(AnonymousAuthenticationProvider(), http_client=http_client)
        yield BackendClient(request_adapter)


@pytest.fixture(scope="session", autouse=True)
def running_application(backend_client_session: BackendClient):
    backend_url = backend_client_session.api.request_adapter.base_url
    assert isinstance(backend_url, str), f"Expected backend_url to be str, got {type(backend_url)} for {backend_url}"
    backend_port = int(backend_url.split(":")[-1])
    exe_process: subprocess.Popen[bytes] | None = None
    if APPLICATION_BOOTUP_MODE == ApplicationBootupModes.DOCKER_COMPOSE:
        start_compose()
    else:
        exe_process = start_exe(port=backend_port)
    yield
    if APPLICATION_BOOTUP_MODE == ApplicationBootupModes.DOCKER_COMPOSE:
        stop_compose()
    else:
        assert exe_process is not None
        stop_exe(process=exe_process, port=backend_port)
