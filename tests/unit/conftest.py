import logging
import tempfile
from collections.abc import Generator

import pytest
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
