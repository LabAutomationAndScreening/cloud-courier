# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from unittest.mock import MagicMock


def logged_message(spy: MagicMock, *, call_index: int = 0) -> str:
    call_args = spy.call_args_list[call_index].args
    assert isinstance(call_args[0], str), f"Expected the logged message to be a str, got {type(call_args[0])}"
    return call_args[0]
