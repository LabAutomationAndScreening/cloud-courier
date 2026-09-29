# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import random
import tempfile
from pathlib import Path
from uuid import uuid4

from backend_api.entrypoint.crash_dump import CRASH_DUMP_FILENAME
from backend_api.entrypoint.crash_dump import resolve_crash_dump_path
from backend_api.entrypoint.crash_dump import write_crash_dump
from backend_api.jinja_constants import APP_NAME


def test_Given_log_folder_in_service_argv__When_resolved__Then_path_is_log_folder_joined_with_filename():
    log_folder = str(Path(tempfile.gettempdir()) / str(uuid4()))

    resolved = resolve_crash_dump_path(["--log-folder", log_folder])

    assert resolved == Path(log_folder) / CRASH_DUMP_FILENAME


def test_Given_no_log_folder_in_service_argv__When_resolved__Then_path_falls_back_to_tempdir():
    resolved = resolve_crash_dump_path(["--port", str(random.randint(1000, 9999))])

    assert resolved == Path(tempfile.gettempdir()) / f"{APP_NAME}-{CRASH_DUMP_FILENAME}"


def test_Given_unparsable_service_argv__When_resolved__Then_path_falls_back_to_tempdir_without_raising():
    resolved = resolve_crash_dump_path(["--port", str(uuid4())])

    assert resolved == Path(tempfile.gettempdir()) / f"{APP_NAME}-{CRASH_DUMP_FILENAME}"


def test_Given_traceback_text__When_crash_dump_written__Then_file_contains_traceback(tmp_path: Path):
    crash_dump_path = tmp_path / CRASH_DUMP_FILENAME
    traceback_text = str(uuid4())

    wrote = write_crash_dump(crash_dump_path=crash_dump_path, traceback_text=traceback_text)

    assert wrote is True
    assert crash_dump_path.exists()
    assert crash_dump_path.read_text(encoding="utf-8") == traceback_text


def test_Given_unwritable_path__When_crash_dump_written__Then_returns_false_without_raising(tmp_path: Path):
    crash_dump_path = tmp_path / str(uuid4()) / CRASH_DUMP_FILENAME
    traceback_text = str(uuid4())

    wrote = write_crash_dump(crash_dump_path=crash_dump_path, traceback_text=traceback_text)

    assert wrote is False
    assert not crash_dump_path.exists()
