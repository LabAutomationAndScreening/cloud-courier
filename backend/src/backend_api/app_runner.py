# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
import logging
import signal
import threading
from pathlib import Path

import uvicorn

from .app_def import app
from .jinja_constants import APP_NAME
from .logger_config import configure_logging

logger = logging.getLogger(__name__)


def app_specific_setup():
    pass


def run(*, stop_event: threading.Event, host: str, port: int, log_level: str) -> int:
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level=log_level))

    def watch_for_stop():
        _ = stop_event.wait()
        server.should_exit = True

    watcher = threading.Thread(target=watch_for_stop, daemon=True)
    watcher.start()
    server.run()
    stop_event.set()
    watcher.join()
    return 0


def start_app(cli_args: argparse.Namespace, *, stop_event: threading.Event | None = None) -> int:
    log_folder = Path("logs")
    if cli_args.log_folder is not None:
        log_folder = Path(cli_args.log_folder)
    configure_logging(
        log_level=cli_args.log_level,
        log_filename_prefix=str(log_folder / f"{APP_NAME}-"),
        # specific to this repository: some SSM Run Commands cannot cope with console output
        suppress_console_logging=bool(cli_args.no_console_logging),
    )
    app_specific_setup()
    logger.info(f"Starting uvicorn server based on CLI arguments: {cli_args}")
    if stop_event is None:
        effective_stop_event = threading.Event()
        _ = signal.signal(signal.SIGINT, lambda _sig, _frame: effective_stop_event.set())  # noqa: ARG005 # signal handler signature requires these args but they are unused
        _ = signal.signal(signal.SIGTERM, lambda _sig, _frame: effective_stop_event.set())  # noqa: ARG005 # signal handler signature requires these args but they are unused
    else:
        effective_stop_event = stop_event
    assert isinstance(cli_args.log_level, str), f"Expected log_level to be a str, got {type(cli_args.log_level)}"
    # specific to this repository: the app's lifespan reads these to start the upload agent alongside the
    # server, following the same convention as `app.state.port` in the sibling weight-sensor-driver repo
    app.state.courier_args = cli_args
    app.state.stop_event = effective_stop_event
    exit_code = run(
        stop_event=effective_stop_event,
        host=cli_args.host,
        port=cli_args.port,
        log_level=cli_args.log_level.lower(),
    )
    try:
        courier_failed = app.state.courier_failed
    except AttributeError:
        courier_failed = False
    if courier_failed:
        # a crashed upload agent must not look like a clean admin stop to the service control manager
        return 1
    return exit_code
