# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import IO

import httpx

from .jinja_constants import APP_NAME
from .jinja_constants import APPLICATION_BOOTUP_MODE
from .jinja_constants import BACKEND_PORT
from .jinja_constants import ApplicationBootupModes

logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"
DEFAULT_COMPOSE_FILE = Path(__file__).parent.parent.parent.parent / "docker-compose.yaml"
EXE_DIR_PATH = Path(__file__).parent.parent.parent / "dist" / APP_NAME
E2E_BACKEND_LOG_DIR = Path(__file__).parent.parent.parent / "dist" / "e2e-backend-logs"
EXE_FILE_NAME = APP_NAME + (".exe" if IS_WINDOWS else "")
EXE_FILE_PATH = EXE_DIR_PATH / EXE_FILE_NAME


def get_random_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))  # Bind to an available ephemeral port
        port = s.getsockname()[1]
        assert isinstance(port, int)
        return port


def _backend_port() -> int:
    if APPLICATION_BOOTUP_MODE == ApplicationBootupModes.DOCKER_COMPOSE:
        return BACKEND_PORT
    return (  # in Windows CI, ports sometimes become unavailable, so we need a random one for executable testing
        get_random_open_port()
    )


BACKEND_E2E_PORT = _backend_port()


def wait_for_backend_to_be_healthy(*, port: int, max_retries: int = 15, retry_delay: int = 2):
    url = f"http://localhost:{port}/api/healthcheck"
    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=5.0)
            if response.is_success:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Backend is healthy!")
                return

            logger.info(f"Attempt {attempt + 1}/{max_retries}: Backend returned status {response.status_code}")
        except httpx.HTTPError as e:
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Failed to connect to backend: {e}")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    raise RuntimeError(f"Backend failed to become healthy after {max_retries} attempts")


def wait_for_service_to_be_healthy(*, max_retries: int = 15, retry_delay: int = 2, compose_file: Path):
    for attempt in range(max_retries):
        try:
            # Get container health status using docker ps
            result = subprocess.run(  # noqa: S603 # we trust this input
                [  # noqa: S607 # docker should definitely be in PATH
                    "docker",
                    "compose",
                    "--file",
                    str(compose_file),
                    "ps",
                    "--format",
                    "json",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )

            if len(result.stdout.strip()) == 0:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Container info not available yet")
                time.sleep(retry_delay)
                continue

            container_info = [json.loads(line) for line in result.stdout.splitlines()]
            health_statuses: dict[str, str] = {}
            for service_info in container_info:
                assert isinstance(service_info, dict), f"Expected dict, got {type(service_info)} for {service_info}"
                health_statuses[service_info["Service"]] = service_info["Health"]

            logger.info(f"Attempt {attempt + 1}/{max_retries}: Container health status: {health_statuses}")

            if all(status in ("healthy", "") for status in health_statuses.values()):
                logger.info("Application containers are healthy!")
                break
        except Exception:
            logger.exception(f"Attempt {attempt + 1}/{max_retries}: Error checking container health:")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    else:
        raise RuntimeError(f"Application containers failed to become healthy after {max_retries} attempts")


def get_services_from_compose(compose_file: Path) -> dict[str, dict[str, str]]:
    result = subprocess.run(  # noqa: S603 # we trust this input
        [  # noqa: S607 # docker should definitely be in PATH
            "docker",
            "compose",
            "--file",
            str(compose_file),
            "config",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    config = json.loads(result.stdout)
    all_services = config.get("services", {})
    assert isinstance(all_services, dict), f"Expected services to be a dict, got {type(all_services)}: {all_services}"
    return all_services


def get_images_from_compose(compose_file: Path, *, services: list[str] | None = None) -> list[str]:
    all_services = get_services_from_compose(compose_file)
    relevant = {name: svc for name, svc in all_services.items() if services is None or name in services}
    return [s["image"] for s in relevant.values() if "image" in s and "build" not in s]


def image_exists_locally(image: str) -> bool:
    result = subprocess.run(  # noqa: S603 # we trust this input
        [  # noqa: S607 # docker should definitely be in PATH
            "docker",
            "image",
            "inspect",
            image,
        ],
        check=False,
        capture_output=True,
        timeout=5,
    )
    return result.returncode == 0


def pull_images(*, compose_file: Path = DEFAULT_COMPOSE_FILE, services: list[str] | None = None):
    images = get_images_from_compose(compose_file, services=services)
    for image in images:
        if image_exists_locally(image):
            logger.info(f"Image already exists locally: {image}")
            continue
        logger.info(f"Pulling image: {image}")
        _ = subprocess.run(  # noqa: S603 # we trust this input
            [  # noqa: S607 # docker should definitely be in PATH
                "docker",
                "pull",
                image,
            ],
            check=True,
            timeout=75,
        )


def start_compose(
    *,
    compose_file: Path = DEFAULT_COMPOSE_FILE,
    services_to_build: list[str] | None = None,
    services_to_start: list[str] | None = None,
):
    assert compose_file.exists(), f"Compose file {compose_file} does not exist"
    if "CI" not in os.environ:
        if services_to_build is None:
            build_targets: list[str] = []
        else:
            build_targets = services_to_build
        _ = subprocess.run(  # noqa: S603 # we trust this input
            [  # noqa: S607 # docker should definitely be in PATH
                "docker",
                "compose",
                "--file",
                str(compose_file),
                "build",
                *build_targets,
            ],
            check=True,
            timeout=300,
        )
    pull_images(compose_file=compose_file, services=services_to_start)
    if services_to_start is None:
        start_targets: list[str] = []
    else:
        start_targets = services_to_start
    extra_up_args: list[str] = []
    if "frontend" in get_services_from_compose(compose_file) and (
        services_to_start is None or "frontend" not in services_to_start
    ):
        extra_up_args.extend(["--scale", "frontend=0"])
    _ = subprocess.run(  # noqa: S603 # we trust this input
        [  # noqa: S607 # docker should definitely be in PATH
            "docker",
            "compose",
            "--file",
            str(compose_file),
            "up",
            "--detach",
            "--no-build",  # without this, the frontend will attempt to be built even though scale=0. We already prebuild the images in an earlier step anyway
            "--force-recreate",
            "--renew-anon-volumes",
            "--remove-orphans",
            *extra_up_args,
            *start_targets,
        ],
        check=True,
        timeout=60,
    )
    try:
        wait_for_service_to_be_healthy(compose_file=compose_file)
    except Exception:
        logger.exception("Failed to verify service health, cleaning up...")
        stop_compose(compose_file=compose_file)
        raise


def stop_compose(*, compose_file: Path = DEFAULT_COMPOSE_FILE):
    assert compose_file.exists(), f"Compose file {compose_file} does not exist"
    _ = subprocess.run(  # noqa: S603 # we trust this input
        [  # noqa: S607 # docker should definitely be in PATH
            "docker",
            "compose",
            "--file",
            str(compose_file),
            "down",
            "--volumes",
        ],
        check=True,
        timeout=45,
    )


def start_exe(*, port: int, env: dict[str, str] | None = None) -> subprocess.Popen[bytes]:
    assert EXE_FILE_PATH.exists(), f"Executable file {EXE_FILE_PATH} does not exist"
    if env is None:
        env = (  # by default, pass in any environmental variables configured during the test setup process
            os.environ.copy()
        )
    E2E_BACKEND_LOG_DIR.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(  # noqa: S603 # we trust this input
        [
            str(EXE_FILE_PATH),
            "--port",
            str(port),
            "--host",
            "0.0.0.0",  # noqa: S104 # until we get Windows CI fully figured out, we're just binding everything
            "--log-folder",  # the backend also writes its own structured JSON log here; CI uploads it on failure
            str(E2E_BACKEND_LOG_DIR),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Both pipes MUST be drained: an unread PIPE fills its OS buffer and blocks the backend (deadlocks readily on
    # Windows). We mirror each line to our own stream so the backend's output stays visible in the CI job log.
    def _drain(stream: IO[bytes] | None, *, mirror: IO[str]) -> None:
        assert stream is not None
        for raw_line in stream:
            _ = mirror.write(raw_line.decode("utf-8", errors="replace"))
            mirror.flush()

    _ = threading.Thread(target=_drain, args=(process.stdout,), kwargs={"mirror": sys.stdout}, daemon=True).start()
    _ = threading.Thread(target=_drain, args=(process.stderr,), kwargs={"mirror": sys.stderr}, daemon=True).start()

    wait_for_backend_to_be_healthy(port=port)
    return process


def stop_exe(*, process: subprocess.Popen[bytes], port: int):
    shutdown_url = f"http://localhost:{port}/api/shutdown"
    try:
        response = httpx.get(shutdown_url, timeout=5.0)
        if response.is_success:
            logger.info("Shutdown request sent successfully.")
        else:
            logger.warning(f"Shutdown request returned status code {response.status_code}.")
    except httpx.HTTPError:
        logger.exception("Failed to send shutdown request")

    # Poll to see if process shut down gracefully
    max_attempts = 10
    poll_interval = 0.5  # seconds
    for attempt in range(max_attempts):
        if process.poll() is not None:
            logger.info(f"The /shutdown route successfully stopped the process. This took {attempt * poll_interval}s.")
            return
        time.sleep(poll_interval)

    if process.poll() is None:
        process.terminate()
        try:
            _ = process.wait(timeout=10)
            logger.info("Executable process terminated gracefully.")
        except subprocess.TimeoutExpired:
            process.kill()
            logger.warning("Executable process killed after timeout.")
