# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
import os
import sys
from collections.abc import Sequence

# SeServiceLogonRight (log-on-as-service) is required by ANY custom service
# account. Additional privileges are app-specific and come from the template's
# extra_windows_service_rights answer (e.g. SeCreateSymbolicLinkPrivilege).
SERVICE_ACCOUNT_RIGHTS = ["SeServiceLogonRight"]

_parser = argparse.ArgumentParser(prog="grant-service-rights")
_ = _parser.add_argument(
    "--account", type=str, required=True, help="The account to grant the Cloud Courier service rights to"
)


def _resolvable_account_name(account: str) -> str:
    local_prefix = ".\\"
    if account.startswith(local_prefix):
        return account[len(local_prefix) :]
    return account


def _grant_account_rights(account: str) -> None:  # pragma: no cover # OS-specific LSA policy call; mocked in tests
    if os.name == "nt":
        import win32security  # noqa: PLC0415 # pywin32, Windows-only, lazy

        sid = win32security.LookupAccountName(None, _resolvable_account_name(account))[0]
        policy = win32security.LsaOpenPolicy(None, win32security.POLICY_ALL_ACCESS)
        try:
            win32security.LsaAddAccountRights(policy, sid, SERVICE_ACCOUNT_RIGHTS)
        finally:
            win32security.LsaClose(policy)


def grant_service_rights(*, account: str) -> int:
    try:
        _grant_account_rights(account)
    except Exception as error:  # noqa: BLE001 # boundary: the failure must become a non-zero exit for the installer, never a traceback
        print(f"Failed to grant service rights to {account}: {error}", file=sys.stderr)  # noqa: T201 # surfaces in the installer log
        return 1
    return 0


def dispatch_grant_rights(argv: Sequence[str]) -> int:
    args = _parser.parse_args(argv)
    return grant_service_rights(account=args.account)
