# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import logging
import random
import signal
import tempfile
import threading

import pytest
import uvicorn
from pytest_mock import MockerFixture

# cloud-courier's parser marks --aws-region and --stop-flag-dir as required, so every entrypoint
# invocation in these template-provided tests has to supply them.
GENERIC_REQUIRED_CLI_ARGS: tuple[str, ...] = (
    "--aws-region=us-east-1",
    f"--stop-flag-dir={tempfile.gettempdir()}",
)


@pytest.fixture(autouse=True)
def restore_logging_levels():
    yield

    # Restore all backend_api loggers and root logger to INFO level
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith("backend_api"):
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)

    logging.getLogger().setLevel(logging.INFO)


@pytest.fixture(autouse=True)
def restore_signal_handlers():
    # entrypoint() registers SIGINT/SIGTERM handlers process-globally when called without a
    # stop_event. Without restoration, Ctrl+C in subsequent pytest runs hits our lambda (which
    # sets a dangling Event nobody reads) instead of pytest's KeyboardInterrupt handler.
    saved_sigint = signal.getsignal(signal.SIGINT)
    saved_sigterm = signal.getsignal(signal.SIGTERM)
    yield
    _ = signal.signal(signal.SIGINT, saved_sigint)
    _ = signal.signal(signal.SIGTERM, saved_sigterm)


def random_non_info_log_level() -> str:
    return random.choice(["DEBUG", "WARNING", "ERROR", "CRITICAL"])


def patch_server_run(mocker: MockerFixture, *, side_effect: object = None) -> None:
    _ = mocker.patch.object(uvicorn.Server, uvicorn.Server.run.__name__, autospec=True, side_effect=side_effect)


def blocking_serve(self_server: uvicorn.Server) -> None:
    while not self_server.should_exit:
        _ = threading.Event().wait(timeout=0.001)
