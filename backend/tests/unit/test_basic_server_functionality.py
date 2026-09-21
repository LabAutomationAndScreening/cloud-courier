# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import time

from backend_api import app_def
from backend_api import fast_api_exception_handlers
from backend_api.app_def import HealthcheckResponse
from backend_api.app_def import app
from fastapi.testclient import TestClient
from httpx import codes
from pytest_mock import MockerFixture
from syrupy.assertion import SnapshotAssertion


def test_Given_healthy__When_healthcheck__Then_version_in_response():
    client = TestClient(app)

    response = client.get("/api/healthcheck")

    assert response.status_code == codes.OK
    actual_version = HealthcheckResponse.model_validate(response.json()).version

    assert actual_version.startswith("v") is False
    assert len(actual_version) > 2  # noqa: PLR2004 # just asserting there's some content that isn't just the period
    assert "." in actual_version


def test_Given_healthy__When_healthcheck_with_prepend_v__Then_version_in_response():
    client = TestClient(app)

    response = client.get("/api/healthcheck?prependV=true")

    assert response.status_code == codes.OK
    actual_version = HealthcheckResponse.model_validate(response.json()).version

    assert actual_version.startswith("v") is True
    assert len(actual_version) > 2  # noqa: PLR2004 # just asserting there's some content that isn't just the period
    assert "." in actual_version


def test_When_swagger_route_called__Then_rendered():
    client = TestClient(app)

    response = client.get("/api-docs")

    assert response.status_code == codes.OK
    assert "Swagger UI" in response.text


def test_When_shutdown_route_called__Then_system_exit(mocker: MockerFixture):
    client = TestClient(app)
    mocked_os_exit = mocker.patch.object(app_def.os, "_exit", autospec=True)

    response = client.get("/api/shutdown")

    assert response.status_code == codes.OK

    for _ in range(1000):  # wait for the thread to finish
        if mocked_os_exit.call_count > 0:
            break
        time.sleep(0.001)
    mocked_os_exit.assert_called_once_with(0)


def test_openapi_schema(snapshot_json: SnapshotAssertion, mocker: MockerFixture):
    client = TestClient(app)
    app.openapi_schema = None  # reset cache populated by other tests
    spied_get_openapi = mocker.spy(fast_api_exception_handlers, "get_openapi")

    response = client.get("/api/openapi.json")

    assert response.status_code == codes.OK
    assert response.json() == snapshot_json
    assert spied_get_openapi.call_count == 1

    re_response = client.get("/api/openapi.json")
    assert re_response.status_code == codes.OK
    assert re_response.text == response.text
    assert spied_get_openapi.call_count == 1  # still 1, not reinvoked
