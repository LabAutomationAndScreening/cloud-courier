import argparse
import logging
import threading
import uuid
from unittest.mock import MagicMock

import pytest
import uvicorn
from backend_api import app_def
from backend_api import app_runner
from backend_api.app_def import app
from backend_api.entrypoint.cli import entrypoint
from backend_api.entrypoint.parser import parser
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

GENERIC_COURIER_CLI_ARGS = ["--aws-region=us-east-1", "--stop-flag-dir=/tmp"]


@pytest.fixture
def spied_start_courier(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(app_def, app_def.start_courier.__name__, autospec=True)


def _set_courier_args(extra_args: list[str] | None = None) -> threading.Event:
    if extra_args is None:
        extra_args = []
    stop_event = threading.Event()
    app.state.courier_args = parser.parse_args([*GENERIC_COURIER_CLI_ARGS, *extra_args])
    app.state.stop_event = stop_event
    return stop_event


class TestWhenAppServed:
    def test_Given_no_cli_args_on_app_state__Then_upload_agent_not_started(self, spied_start_courier: MagicMock):
        assert hasattr(app.state, "courier_args") is False

        with TestClient(app) as client:
            response = client.get("/api/healthcheck")

        assert response.is_success
        spied_start_courier.assert_not_called()

    def test_Given_skip_upload_agent__Then_upload_agent_not_started(self, spied_start_courier: MagicMock):
        _ = _set_courier_args(["--skip-upload-agent"])

        with TestClient(app) as client:
            response = client.get("/api/healthcheck")

        assert response.is_success
        spied_start_courier.assert_not_called()

    def test_Given_cli_args_on_app_state__Then_upload_agent_started_with_them(self, spied_start_courier: MagicMock):
        stop_event = _set_courier_args()

        with TestClient(app):
            pass

        spied_start_courier.assert_called_once_with(app.state.courier_args, stop_event=stop_event)

    def test_Given_upload_agent_running__When_app_shuts_down__Then_stop_event_set(
        self, spied_start_courier: MagicMock
    ):
        agent_started = threading.Event()

        def _wait_for_stop(_cli_args: argparse.Namespace, *, stop_event: threading.Event) -> int:
            agent_started.set()
            _ = stop_event.wait()
            return 0

        spied_start_courier.side_effect = _wait_for_stop
        stop_event = _set_courier_args()

        with TestClient(app):
            assert agent_started.wait(timeout=5) is True
            assert stop_event.is_set() is False

        assert stop_event.is_set() is True

    def test_Given_upload_agent_raises__Then_failure_recorded_and_stop_event_set(
        self, spied_start_courier: MagicMock
    ):
        spied_start_courier.side_effect = RuntimeError(str(uuid.uuid4()))
        stop_event = _set_courier_args()

        with TestClient(app):
            assert stop_event.wait(timeout=5) is True

        assert app.state.courier_failed is True

    def test_Given_upload_agent_does_not_stop__Then_error_logged(
        self, spied_start_courier: MagicMock, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ):
        never_released = threading.Event()

        def _ignore_stop(_cli_args: argparse.Namespace, *, stop_event: threading.Event) -> int:  # noqa: ARG001 # this agent deliberately ignores the stop event
            _ = never_released.wait()
            return 0

        spied_start_courier.side_effect = _ignore_stop
        _ = mocker.patch.object(app_def, "COURIER_SHUTDOWN_TIMEOUT_SECONDS", 0.01)
        _ = _set_courier_args()

        with caplog.at_level(logging.ERROR), TestClient(app):
            pass

        never_released.set()
        assert "did not stop within" in caplog.text


class TestWhenAppRun:
    def test_Given_upload_agent_failed__Then_non_zero_exit_code(self, mocker: MockerFixture):
        def _fail_the_agent(*, stop_event: threading.Event, host: str, port: int, log_level: str) -> int:  # noqa: ARG001 # the signature has to match app_runner.run
            app.state.courier_failed = True
            return 0

        _ = mocker.patch.object(app_runner, app_runner.run.__name__, autospec=True, side_effect=_fail_the_agent)

        assert entrypoint(["--skip-upload-agent"]) == 1

    def test_Given_upload_agent_did_not_fail__Then_zero_exit_code(self, mocker: MockerFixture):
        _ = mocker.patch.object(uvicorn.Server, uvicorn.Server.run.__name__, autospec=True)

        assert entrypoint(["--skip-upload-agent"]) == 0
