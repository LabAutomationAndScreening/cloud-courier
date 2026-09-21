# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
from importlib.metadata import version

from ..jinja_constants import APP_NAME
from ..jinja_constants import DEFAULT_DEPLOYED_HOST
from ..jinja_constants import DEPLOYED_PORT_NUMBER


# pragma: no mutate start
def get_version(
    *,
    # mutmut isn't picking up the fact that this function gets called when the OpenAPI Schema snapshot gets taken, which causes mutating the default value to be caught
    prepend_v: bool = False,
) -> str:
    # pragma: no mutate end
    # pragma: no mutate start
    # This is the name of the package as defined in pyproject.toml # TODO: figure out if there's a way with mutmut to avoid just the case-sensitivity mutations
    version_str = version("backend-api")
    # pragma: no mutate end
    if prepend_v:
        version_str = f"v{version_str}"
    return version_str


parser = argparse.ArgumentParser(description=APP_NAME, exit_on_error=False)
_ = parser.add_argument("--version", action="version", version=get_version(prepend_v=True))
_ = parser.add_argument("--log-level", type=str, default="INFO", help="The log level to use for the logger")
_ = parser.add_argument("--log-folder", type=str, help="The folder to write logs to")
_ = parser.add_argument("--port", type=int, default=DEPLOYED_PORT_NUMBER, help="What port to serve the app on")
_ = parser.add_argument("--host", type=str, default=DEFAULT_DEPLOYED_HOST, help="What hosts to allow connections from")
