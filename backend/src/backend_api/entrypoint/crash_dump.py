# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
import tempfile
from collections.abc import Sequence
from pathlib import Path

from ..jinja_constants import APP_NAME
from .parser import parser

CRASH_DUMP_FILENAME = "service-crash.log"


def resolve_crash_dump_path(service_argv: Sequence[str]) -> Path:
    """Pick a writable dir for the crash dump.

    Preference order: --log-folder from service_argv (already writable, captured by CI artifact),
    then the system temp dir (LocalSystem-writable fallback for production installs in
    Program Files where the exe dir is read-only).
    """
    try:
        args, _ = parser.parse_known_args(service_argv)
        log_folder = args.log_folder
        assert log_folder is None or isinstance(log_folder, str)
    except (argparse.ArgumentError, SystemExit):
        log_folder = None
    if log_folder is not None:
        return Path(log_folder) / CRASH_DUMP_FILENAME
    return Path(tempfile.gettempdir()) / f"{APP_NAME}-{CRASH_DUMP_FILENAME}"


def write_crash_dump(*, crash_dump_path: Path, traceback_text: str) -> bool:
    try:
        _ = crash_dump_path.write_text(traceback_text, encoding="utf-8")
    except OSError:
        return False
    return True
