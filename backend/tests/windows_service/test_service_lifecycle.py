# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import logging
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from backend_api.entrypoint.crash_dump import CRASH_DUMP_FILENAME
from backend_api.jinja_constants import WINDOWS_SERVICE_NAME

from ..e2e.app_bootup import EXE_FILE_PATH
from ..e2e.app_bootup import get_random_open_port
from ..e2e.app_bootup import wait_for_backend_to_be_healthy

logger = logging.getLogger(__name__)
_SUBCOMMAND_TIMEOUT = 30
_SC_TIMEOUT = 10
_STOP_TIMEOUT = 30
_CRASH_DUMP_POLL_TIMEOUT = 60
_EXE = str(EXE_FILE_PATH)
_ERROR_SERVICE_SPECIFIC_ERROR = "1066"  # Windows WIN32_EXIT_CODE indicating app-specific failure


@dataclass(frozen=True)
class InstalledService:
    port: int
    log_folder: Path
    crash_dump_path: Path


def _run_app(*args: str, check: bool = True, timeout: int = _SUBCOMMAND_TIMEOUT) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 # we trust this input
        [_EXE, *args],
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def _run_sc(*args: str, check: bool = False) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 # sc.exe is a trusted Windows system utility
        ["sc", *args],  # noqa: S607 # sc.exe is a Windows system binary always available in PATH
        capture_output=True,
        timeout=_SC_TIMEOUT,
        check=check,
    )


def _install_service(*, port: int, log_folder: Path, extra_runtime_args: Sequence[str] = ()) -> None:
    _ = _run_app(
        "service",
        "install",
        "--",
        "--port",
        str(port),
        "--log-folder",
        str(log_folder),
        "--host",
        "0.0.0.0",  # noqa: S104 # match e2e pattern: bind everything until Windows CI networking sorted out
        # specific to this repository: the Windows CI runner has no AWS account to reach, and an upload agent
        # that cannot reach AWS stops the whole process, which would look like a service crash
        "--skip-upload-agent",
        *extra_runtime_args,
    )


def _uninstall_service() -> None:
    stop = _run_app("service", "stop", check=False)
    if stop.returncode != 0:
        logger.warning("service stop exited %d: %s", stop.returncode, stop.stderr.decode())
    remove = _run_app("service", "remove", check=False)
    if remove.returncode != 0:
        logger.warning("service remove exited %d: %s", remove.returncode, remove.stderr.decode())


@pytest.fixture
def installed_service(tmp_path: Path):
    port = get_random_open_port()
    log_folder = tmp_path / "service-logs"
    log_folder.mkdir()
    crash_dump_path = log_folder / CRASH_DUMP_FILENAME
    _install_service(port=port, log_folder=log_folder)
    try:
        yield InstalledService(port=port, log_folder=log_folder, crash_dump_path=crash_dump_path)
    finally:
        if crash_dump_path.exists():
            logger.error("service worker crash dump:\n%s", crash_dump_path.read_text(encoding="utf-8"))
        _uninstall_service()


@pytest.mark.usefixtures(installed_service.__name__)
def test_Given_service_installed__Then_registered_in_scm():
    result = _run_sc("query", WINDOWS_SERVICE_NAME)

    assert result.returncode == 0


@pytest.mark.usefixtures(installed_service.__name__)
def test_When_service_installed__Then_imagepath_contains_service_token():
    result = _run_sc("qc", WINDOWS_SERVICE_NAME, check=True)

    binary_path_line = next(
        (line for line in result.stdout.decode().splitlines() if "BINARY_PATH_NAME" in line),
        "",
    )
    # ImagePath format: "<exe>" service --port <n> --host 0.0.0.0 --log-folder <path>
    assert " service " in binary_path_line


@pytest.mark.timeout(60)
def test_Given_service_started__When_healthcheck_called__Then_success(installed_service: InstalledService):
    _ = _run_app("service", "start")

    wait_for_backend_to_be_healthy(port=installed_service.port)
    response = httpx.get(f"http://localhost:{installed_service.port}/api/healthcheck", timeout=5.0)

    assert response.is_success


@pytest.mark.timeout(120)
def test_Given_service_started_then_stopped__When_healthcheck_called__Then_no_longer_reachable(
    installed_service: InstalledService,
):
    _ = _run_app("service", "start")
    wait_for_backend_to_be_healthy(port=installed_service.port)

    _ = _run_app("service", "stop")

    deadline = time.monotonic() + _STOP_TIMEOUT
    while time.monotonic() < deadline:
        try:
            _ = httpx.get(f"http://localhost:{installed_service.port}/api/healthcheck", timeout=1.0)
            time.sleep(0.5)
        except httpx.TransportError:
            # ConnectError (RST) or ConnectTimeout (no SYN-ACK) both mean the server is no longer
            # serving. Windows can produce either depending on socket cleanup timing.
            return
    pytest.fail(f"Server still reachable {_STOP_TIMEOUT}s after service stop")


@dataclass(frozen=True)
class CrashedService:
    crash_dump_path: Path
    bad_log_level: str


def _log_crash_dump_diagnostics(*, log_folder: Path, start_result: subprocess.CompletedProcess[bytes]) -> None:
    # When the poll loop times out without seeing the crash dump, the failure mode is invisible:
    # could be SCM never started the worker, worker started but write hit OSError, or path
    # resolved elsewhere. Capture state so the next CI failure points at a concrete branch.
    logger.error("service start returncode=%d", start_result.returncode)
    logger.error("service start stdout:\n%s", start_result.stdout.decode(errors="replace"))
    logger.error("service start stderr:\n%s", start_result.stderr.decode(errors="replace"))
    sc_query = _run_sc("query", WINDOWS_SERVICE_NAME)
    logger.error("sc query returncode=%d output:\n%s", sc_query.returncode, sc_query.stdout.decode(errors="replace"))
    if log_folder.exists():
        logger.error("log_folder contents: %s", sorted(p.name for p in log_folder.iterdir()))
    else:
        logger.error("log_folder %s does not exist", log_folder)
    # Pull the most recent Application event log entries for this service; LogErrorMsg from the
    # win_service crash handler lands here when crash dump file write itself failed.
    event_log = subprocess.run(
        ["wevtutil", "qe", "Application", "/c:20", "/rd:true", "/f:text"],  # noqa: S607 # wevtutil is a Windows system binary always available in PATH
        capture_output=True,
        timeout=_SC_TIMEOUT,
        check=False,
    )
    logger.error("recent Application event log entries:\n%s", event_log.stdout.decode(errors="replace"))


@pytest.mark.timeout(120)
class TestServiceWorkerCrash:
    @pytest.fixture
    def crashed_service(self, tmp_path: Path):
        # Bad --log-level passes argparse but trips dictConfig in configure_logging — a ValueError
        # that propagates out of entrypoint and is caught by win_service._run's diagnostic handler.
        bad_log_level = "GARBAGE_LEVEL"
        port = get_random_open_port()
        log_folder = tmp_path / "service-logs"
        log_folder.mkdir()
        crash_dump_path = log_folder / CRASH_DUMP_FILENAME
        _install_service(port=port, log_folder=log_folder, extra_runtime_args=["--log-level", bad_log_level])
        try:
            # SCM may report start success briefly before the worker thread crashes; ignore returncode.
            start_result = _run_app("service", "start", check=False)
            deadline = time.monotonic() + _CRASH_DUMP_POLL_TIMEOUT
            while time.monotonic() < deadline and not crash_dump_path.exists():
                time.sleep(0.5)
            if not crash_dump_path.exists():
                _log_crash_dump_diagnostics(log_folder=log_folder, start_result=start_result)
            yield CrashedService(crash_dump_path=crash_dump_path, bad_log_level=bad_log_level)
        finally:
            # Remove crash dump before CI artifact upload so passing tests don't litter the upload.
            if crash_dump_path.exists():
                crash_dump_path.unlink()
            _uninstall_service()

    def test_When_service_worker_crashes__Then_crash_dump_written_to_log_folder(self, crashed_service: CrashedService):
        assert crashed_service.crash_dump_path.exists(), f"crash dump not written at {crashed_service.crash_dump_path}"
        content = crashed_service.crash_dump_path.read_text(encoding="utf-8")
        assert crashed_service.bad_log_level in content, f"crash dump missing trigger value; content:\n{content}"

    def test_Given_service_worker_crashed__When_scm_query_called__Then_exit_code_is_service_specific_error(
        self, crashed_service: CrashedService
    ):
        # SCM recovery actions (auto-restart on failure) only fire when the service stops with a
        # non-zero exit code. A worker crash must surface to SCM as ERROR_SERVICE_SPECIFIC_ERROR (1066)
        # so operators can configure recovery policies and monitoring can distinguish crashes from
        # clean admin stops.
        assert crashed_service.crash_dump_path.exists()

        result = _run_sc("query", WINDOWS_SERVICE_NAME, check=True)

        output = result.stdout.decode()
        assert "STOPPED" in output, f"service not in STOPPED state; sc query output:\n{output}"
        assert _ERROR_SERVICE_SPECIFIC_ERROR in output, (
            f"expected WIN32_EXIT_CODE {_ERROR_SERVICE_SPECIFIC_ERROR} (ERROR_SERVICE_SPECIFIC_ERROR) after worker crash;\n"
            f"sc query output:\n{output}"
        )


def test_When_install_with_startup_option_before_subcommand__Then_service_registered_with_auto_start(tmp_path: Path):
    # pywin32 uses POSIX getopt, which requires options BEFORE the subcommand
    # (e.g. `service --startup auto install`). Our wrapper must forward this layout intact rather
    # than hardcoding argv[1] as the subcommand.
    port = get_random_open_port()
    log_folder = tmp_path / "service-logs"
    log_folder.mkdir()
    try:
        _ = _run_app(
            "service",
            "--startup",
            "auto",
            "install",
            "--",
            "--port",
            str(port),
            "--log-folder",
            str(log_folder),
            "--host",
            "0.0.0.0",  # noqa: S104 # match e2e pattern
        )

        result = _run_sc("qc", WINDOWS_SERVICE_NAME, check=True)

        output = result.stdout.decode()
        # sc qc reports `START_TYPE         : 2   AUTO_START` for auto-start services
        assert "AUTO_START" in output, f"service not registered with AUTO_START;\nsc qc output:\n{output}"
    finally:
        _uninstall_service()


@pytest.mark.timeout(120)
def test_Given_service_stopped_cleanly__When_scm_query_called__Then_exit_code_is_zero(
    installed_service: InstalledService,
):
    # Counterpart to the crash exit-code test: a clean admin stop must report exit code 0 so it
    # is distinguishable from a crash and does not trigger recovery policies.
    _ = _run_app("service", "start")
    wait_for_backend_to_be_healthy(port=installed_service.port)
    _ = _run_app("service", "stop")

    result = _run_sc("query", WINDOWS_SERVICE_NAME, check=True)

    output = result.stdout.decode()
    assert "STOPPED" in output, f"service not in STOPPED state; sc query output:\n{output}"
    assert _ERROR_SERVICE_SPECIFIC_ERROR not in output, (
        f"clean stop must not report WIN32_EXIT_CODE {_ERROR_SERVICE_SPECIFIC_ERROR};\nsc query output:\n{output}"
    )
