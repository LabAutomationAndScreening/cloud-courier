# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
import logging
import sys
import threading
from collections.abc import Sequence

from .. import app_runner
from .parser import parser

logger = logging.getLogger(__name__)


def entrypoint(argv: Sequence[str], *, stop_event: threading.Event | None = None) -> int:
    try:
        launched_by_uvicorn = len(argv) > 0 and argv[0] == "src.entrypoint:app"
        if launched_by_uvicorn:
            app_runner.app_specific_setup()
            return 0
        if len(argv) > 0 and argv[0] == "grant-service-rights":
            from .grant_rights import dispatch_grant_rights  # noqa: PLC0415 # lazy import to match the service branch

            return dispatch_grant_rights(argv[1:])
        if len(argv) > 0 and argv[0] == "service":
            if sys.platform != "win32":  # pragma: no cover — win32 path tested in Windows CI
                print("Windows service management is only supported on Windows", file=sys.stderr)  # noqa: T201 # intentional user-facing output
                return 2
            # lazy: win_service.py imports pywin32 + winreg, Windows-only (covered in Windows CI)
            from . import win_service  # noqa: PLC0415  # pragma: no cover

            return win_service.dispatch_windows_service(argv)  # pragma: no cover
        try:
            cli_args = parser.parse_args(argv)
        except argparse.ArgumentError:
            logger.exception("Error parsing command line arguments")
            return 2  # this is the exit code that is normally returned when exit_on_error=True for argparse
        return app_runner.start_app(cli_args, stop_event=stop_event)
    except Exception:
        logger.exception("An unhandled exception occurred")
        raise
