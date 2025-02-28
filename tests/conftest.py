import logging
import tempfile
from collections.abc import Generator

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.python import Function
from pytest_mock import MockerFixture

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def localstack_profile(mocker: MockerFixture) -> None:
    mocker.patch.dict(
        "os.environ",
        {
            "AWS_PROFILE": "localstack",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_SESSION_TOKEN": "test",
        },
    )


@pytest.fixture
def flag_file_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--only-exe",
        action="store_true",
        default=False,
        help="only run tests that are marked for the compiled exe",
    )


def pytest_collection_modifyitems(config: Config, items: list[Function]) -> None:
    if config.getoption("--only-exe"):
        skip_non_exe = pytest.mark.skip(
            reason="these tests are skipped when only running tests that only target the compiled .exe file"
        )
        for item in items:
            if "only_exe" not in item.keywords:
                item.add_marker(skip_non_exe)
        return

    skip_exe = pytest.mark.skip(reason="these tests are skipped unless --only-exe option is set")
    for item in items:
        if "only_exe" in item.keywords:
            item.add_marker(skip_exe)
