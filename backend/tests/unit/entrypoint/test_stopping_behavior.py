# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import os
import signal
import sys
import threading

import pytest
import uvicorn
from backend_api.entrypoint.cli import entrypoint
from pytest_mock import MockerFixture

from .fixtures import GENERIC_REQUIRED_CLI_ARGS
from .fixtures import blocking_serve
from .fixtures import patch_server_run
from .fixtures import restore_logging_levels  # noqa: F401 # autouse fixture imported for side effect
from .fixtures import restore_signal_handlers  # noqa: F401 # autouse fixture imported for side effect


@pytest.mark.timeout(10)
class TestStoppingBehavior:
    @pytest.fixture(autouse=True)
    def _setup(self, mocker: MockerFixture):
        self.stop_event = threading.Event()
        self._server_started = threading.Event()
        self._server_instance: uvicorn.Server | None = None
        self._entrypoint_thread: threading.Thread | None = None

        def _blocking_serve(self_server: uvicorn.Server) -> None:
            self._server_instance = self_server
            self._server_started.set()
            blocking_serve(self_server)

        _ = mocker.patch.object(uvicorn.Server, uvicorn.Server.run.__name__, autospec=True, side_effect=_blocking_serve)

    def _run_entrypoint(self) -> None:
        self._entrypoint_thread = threading.Thread(
            target=entrypoint,
            args=(GENERIC_REQUIRED_CLI_ARGS,),
            kwargs={"stop_event": self.stop_event},
            daemon=True,
        )
        self._entrypoint_thread.start()
        assert self._server_started.wait(timeout=2), "server never started"

    def _wait_for_entrypoint_to_exit(self) -> None:
        assert self._entrypoint_thread is not None, "_run_entrypoint must be called before waiting for exit"
        self._entrypoint_thread.join(timeout=2)
        assert not self._entrypoint_thread.is_alive(), "entrypoint thread did not exit within 2s"

    def test_Given_stop_event_pre_set__Then_server_should_exit_flipped_true(self):
        self.stop_event.set()

        self._run_entrypoint()
        self._wait_for_entrypoint_to_exit()

        assert self._server_instance is not None
        assert self._server_instance.should_exit is True

    def test_Given_stop_event_not_set__Then_server_should_exit_false_at_serve_start(self):
        self._run_entrypoint()

        assert self._server_instance is not None
        captured_should_exit = self._server_instance.should_exit

        self.stop_event.set()
        self._wait_for_entrypoint_to_exit()
        assert captured_should_exit is False

    def test_Given_stop_event_set_during_serve__Then_server_should_exit_flipped_true(self):
        self._run_entrypoint()

        self.stop_event.set()

        self._wait_for_entrypoint_to_exit()
        assert self._server_instance is not None
        assert self._server_instance.should_exit is True


def test_Given_entrypoint_invoked_without_stop_event__Then_sigint_handler_installed(mocker: MockerFixture):
    patch_server_run(mocker)
    spied_signal_fn = mocker.spy(signal, signal.signal.__name__)

    _ = entrypoint(GENERIC_REQUIRED_CLI_ARGS)

    signals_registered = [call.args[0] for call in spied_signal_fn.call_args_list]
    assert signal.SIGINT in signals_registered


@pytest.mark.timeout(10)
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.kill(SIGINT/SIGTERM) on Windows sends CTRL_C_EVENT to the process group and terminates the CI process rather than invoking the Python signal handler",
)
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_Given_signal_received__Then_entrypoint_exits(mocker: MockerFixture, sig: signal.Signals):
    server_started = threading.Event()

    def _blocking_serve(self_server: uvicorn.Server) -> None:
        server_started.set()
        blocking_serve(self_server)

    patch_server_run(mocker, side_effect=_blocking_serve)

    def fire_signal() -> None:
        assert server_started.wait(timeout=2), "server never started"
        os.kill(os.getpid(), sig)

    t = threading.Thread(target=fire_signal, daemon=True)
    t.start()

    _ = entrypoint(GENERIC_REQUIRED_CLI_ARGS)

    t.join(timeout=2)
    assert not t.is_alive()
