# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import os
from collections.abc import Mapping
from collections.abc import Sequence

# Must match the $env: name set in installer/scripts/install-service.ps1.
SERVICE_INSTALL_PASSWORD_ENV = "WINDOWS_SERVICE_INSTALL_PASSWORD"  # noqa: S105 # this is the env var NAME, not a password value

_INSTALL_SUBCOMMAND = "install"


def inject_install_password(
    install_args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Splice ``--password <value>`` from the environment into an ``install`` arg list.

    install-service.ps1 passes the service password via the environment rather than on the
    exe's command line (which is readable by any local process for the install window). Here
    we read it back and insert it into the in-memory arg list handed to pywin32's
    HandleCommandLine, so the secret reaches CreateService without ever appearing in a
    process command line.

    pywin32 uses POSIX getopt, which requires options before the subcommand, so the flag is
    inserted immediately before the ``install`` verb. The verb is the terminal token, so we
    match the last occurrence -- a ``--username install`` option value must not be mistaken for
    the subcommand. Any other subcommand, an unset/empty password, or an arg list that already
    carries ``--password`` is returned unchanged.
    """
    args = list(install_args)
    if env is None:
        resolved_env = os.environ
    else:
        resolved_env = env
    password = resolved_env.get(SERVICE_INSTALL_PASSWORD_ENV)
    if password is None or password == "":
        return args
    if _INSTALL_SUBCOMMAND not in args:
        return args
    if "--password" in args:
        return args
    idx = len(args) - 1 - args[::-1].index(_INSTALL_SUBCOMMAND)
    return [*args[:idx], "--password", password, *args[idx:]]
