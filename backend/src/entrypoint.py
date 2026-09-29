# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import pip_system_certs.wrapt_requests

# ruff: noqa: E402 # we need to inject the truststore before we import anything else
pip_system_certs.wrapt_requests.inject_truststore()
import sys

from backend_api.app_def import app  # noqa: F401 # this needs to be imported for the FastAPI app to actually launch
from backend_api.entrypoint.cli import entrypoint

exit_code = entrypoint(sys.argv[1:])
if (  # needed to enable using hot-reloading with uvicorn. if we always call sys.exit even with 0, then the FastAPI app won't work correctly when launched directly by uvicorn
    exit_code != 0
):
    sys.exit(exit_code)
