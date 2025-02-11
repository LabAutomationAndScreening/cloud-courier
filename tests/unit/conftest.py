import logging
import tempfile
from collections.abc import Generator

import pytest

logger = logging.getLogger(__name__)


@pytest.fixture
def flag_file_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir
