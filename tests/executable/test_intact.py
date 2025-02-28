import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.only_exe
class TestExeIsIntact:
    @pytest.fixture(autouse=True)
    def _setup(self):
        exe_file_name = f"cloud-courier{'.exe' if os.name == 'nt' else ''}"
        self.path_to_exe = Path(__file__).parent.parent.parent / "dist" / "cloud-courier" / exe_file_name

        assert self.path_to_exe.exists(), f"Expected {self.path_to_exe} to exist"

    def test_version(self):
        result = subprocess.run(  # noqa: S603 # this is known trusted input
            [self.path_to_exe, "--version"], capture_output=True, text=True, check=True
        )

        actual_version = result.stdout.strip()

        assert actual_version.startswith("v")
