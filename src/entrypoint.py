# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-python-package-template
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import sys  # pragma: no cover # we can't unit test the entrypoint itself. It is tested in the E2E test of the executable

from cloud_courier.main import (
    entrypoint,
)  # pragma: no cover # we can't unit test the entrypoint itself. It is tested in the E2E test of the executable

if __name__ == "__main__":
    sys.exit(entrypoint(sys.argv[1:]))
