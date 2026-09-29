# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import os
import subprocess
import sys
import threading
import traceback
from collections.abc import Sequence
from pathlib import Path

# pywin32 is win32-only, so the per-import missing-import ignores are required in CI/Linux but appear unnecessary on Windows dev machines.
import servicemanager  # pyrefly: ignore[missing-import,unused-ignore] # pywin32 has no stubs; only importable on Windows
import win32service  # pyrefly: ignore[missing-import,unused-ignore] # pywin32 has no stubs; only importable on Windows
import win32serviceutil  # pyrefly: ignore[missing-import,unused-ignore] # pywin32 has no stubs; only importable on Windows
import winerror  # pyrefly: ignore[missing-import,unused-ignore] # pywin32 has no stubs; only importable on Windows

from .. import app_runner
from ..jinja_constants import APP_NAME
from ..jinja_constants import WINDOWS_SERVICE_DISPLAY_NAME
from ..jinja_constants import WINDOWS_SERVICE_NAME
from .crash_dump import resolve_crash_dump_path
from .crash_dump import write_crash_dump
from .parser import parser
from .service_install_password import inject_install_password

_SERVICE_MANAGEMENT_COMMANDS = frozenset({"install", "start", "stop", "remove", "debug"})


class AppService(win32serviceutil.ServiceFramework):
    _svc_name_ = WINDOWS_SERVICE_NAME
    _svc_display_name_ = WINDOWS_SERVICE_DISPLAY_NAME
    _exe_args_ = ""  # set by dispatch_windows_service before install; pywin32 reads this to build ImagePath

    def __init__(self, args: tuple[str, ...]) -> None:
        super().__init__(args)
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._worker_crash_dump_written = False

    def SvcStop(self) -> None:  # noqa: N802 # pywin32 mandates this exact method name
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=30)
            if self._worker.is_alive():
                servicemanager.LogErrorMsg(f"{APP_NAME}: worker did not stop within 30s; SCM will force-terminate")

    def SvcRun(self) -> None:  # noqa: N802 # pywin32 mandates this exact method name
        # Outermost guard pywin32 hands control to. On a slow SCM startup the status handle can already
        # be invalid by the time ReportServiceStatus runs, so a crash anywhere — startup, status
        # reporting, or SvcDoRun itself — could escape before any dump was written. Write the dump as a
        # fallback on ANY unhandled exception, then re-raise so pywin32 still surfaces the failure to SCM
        # as ERROR_SERVICE_SPECIFIC_ERROR (1066). Skip the write when SvcDoRun already captured the real
        # crash: the escaping exception is then the invalid-handle ReportServiceStatus race, whose
        # traceback would otherwise clobber the genuine worker traceback already on disk. The flag tracks
        # what THIS invocation wrote — the dump filename is fixed, so a file left by an earlier crashed
        # run must not suppress capturing the current one.
        crash_dump_path = resolve_crash_dump_path(sys.argv[2:])
        try:
            super().SvcRun()
        except BaseException:
            if not self._worker_crash_dump_written:
                _ = write_crash_dump(crash_dump_path=crash_dump_path, traceback_text=traceback.format_exc())
            raise

    def SvcDoRun(self) -> None:  # noqa: N802 # pywin32 mandates this exact method name
        # TODO: stop reading sys.argv here — couples runtime to global argv layout and the magic [2:] offset.
        # pywin32 passes the command-line args to __init__ via the `args` tuple (args[0] = service name,
        # args[1:] = runtime args), so capture them in __init__ and read self._service_argv here instead.
        # Non-breaking refactor: ImagePath format and installed services unaffected. Also fixes the
        # `service debug` foreground path, which currently feeds "debug" into argparse and crashes.
        service_argv = sys.argv[2:]  # sys.argv[0] = exe path, sys.argv[1] = 'service', sys.argv[2:] = runtime args
        crash_dump_path = resolve_crash_dump_path(service_argv)
        crash_traceback: str | None = None

        def _run() -> None:
            nonlocal crash_traceback
            try:
                # SCM detaches stdio: sys.stdout/sys.stderr are None. uvicorn's DefaultFormatter
                # calls sys.stdout.isatty() during __init__ and crashes. Redirect to devnull;
                # the file logger configured via --log-folder still captures all log output.
                sys.stdout = Path(os.devnull).open("w", encoding="utf-8")  # noqa: SIM115 # service-lifetime handle; closing would break later writes
                sys.stderr = Path(os.devnull).open("w", encoding="utf-8")  # noqa: SIM115 # service-lifetime handle; closing would break later writes
                cli_args = parser.parse_args(service_argv)
                _ = app_runner.start_app(cli_args, stop_event=self._stop_event)
            except BaseException:  # noqa: BLE001 # service-of-last-resort: must also catch SystemExit from argparse (--version/--help/parse errors) so the failure surfaces to SCM + crash dump instead of silently exiting
                crash_traceback = traceback.format_exc()
                self._stop_event.set()
                # don't re-raise: daemon-thread exceptions die silently anyway, so the crash is
                # captured here and handled on the main service thread below after the worker exits.

        self._worker = threading.Thread(target=_run, daemon=True)
        self._worker.start()
        self._worker.join()

        if crash_traceback is not None:
            # Write the dump FIRST and unconditionally — before any event-log or status-reporting call —
            # so a failing ReportServiceStatus (invalid SCM handle) can never prevent the dump file.
            self._worker_crash_dump_written = write_crash_dump(
                crash_dump_path=crash_dump_path, traceback_text=crash_traceback
            )
            if not self._worker_crash_dump_written:
                servicemanager.LogErrorMsg(f"{APP_NAME}: failed to write crash dump to {crash_dump_path}")
            servicemanager.LogErrorMsg(f"{APP_NAME}: worker crashed\n{crash_traceback}")
            # ERROR_SERVICE_SPECIFIC_ERROR (1066) signals to SCM that the service stopped due to an
            # app-defined failure; SCM then exposes svcExitCode for the specific failure code. Non-zero
            # exit lets `sc failure` recovery actions fire and lets monitoring distinguish a worker
            # crash from a clean admin stop. Without this, pywin32 reports SERVICE_STOPPED with
            # win32ExitCode=0, indistinguishable from a normal shutdown.
            self.ReportServiceStatus(
                win32service.SERVICE_STOPPED,
                win32ExitCode=winerror.ERROR_SERVICE_SPECIFIC_ERROR,
                svcExitCode=1,
            )


def dispatch_windows_service(argv: Sequence[str]) -> int:
    # Split at `--`: pre-separator args go to HandleCommandLine (pywin32 SCM management);
    # post-separator args are baked into the service ImagePath so SCM passes them to SvcDoRun at start.
    if "--" in argv:
        sep_idx = argv.index("--")
        install_args = list(argv[1:sep_idx])
        runtime_args = list(argv[sep_idx + 1 :])
    else:
        install_args = list(argv[1:])
        runtime_args: list[str] = []

    # Scan rather than hardcoding argv[1]: pywin32 uses POSIX getopt and expects options before the
    # subcommand (e.g. `service --startup auto install -- ...`), so the subcommand isn't always at
    # index 1. If no _SERVICE_MANAGEMENT_COMMANDS token is present, SCM started us via ImagePath
    # (sys.argv = [exe, "service", "--port=N", ...]) — go to the SCM dispatch branch.
    service_subcommand = next((a for a in install_args if a in _SERVICE_MANAGEMENT_COMMANDS), None)
    if service_subcommand is not None:
        if service_subcommand == "install":
            # pywin32 reads _exe_args_ at install time and bakes the suffix into the ImagePath
            # registry value itself — no post-install registry patching needed.
            AppService._exe_args_ = subprocess.list2cmdline(["service", *runtime_args])
            # The service password arrives via the environment, not the command line (which any
            # local process can read); splice it into the in-memory arg list here so it reaches
            # CreateService without ever appearing in the exe's process command line.
            install_args = inject_install_password(install_args)
        win32serviceutil.HandleCommandLine(AppService, argv=[sys.argv[0], *install_args])
    else:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AppService)
        servicemanager.StartServiceCtrlDispatcher()
    return 0
