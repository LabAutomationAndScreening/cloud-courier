# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
from uuid import uuid4

from backend_api.entrypoint import grant_rights
from backend_api.entrypoint.grant_rights import SERVICE_ACCOUNT_RIGHTS
from backend_api.entrypoint.grant_rights import _resolvable_account_name
from backend_api.entrypoint.grant_rights import dispatch_grant_rights
from backend_api.entrypoint.grant_rights import grant_service_rights
from pytest_mock import MockerFixture


class TestServiceAccountRights:
    def test_Then_service_logon_right_always_granted(self):
        assert "SeServiceLogonRight" in SERVICE_ACCOUNT_RIGHTS


class TestResolvableAccountName:
    def test_Given_dot_backslash_prefix__Then_stripped_to_bare_local_name(self):
        name = uuid4().hex

        assert _resolvable_account_name(f".\\{name}") == name

    def test_Given_domain_qualified__Then_unchanged(self):
        domain = uuid4().hex
        name = uuid4().hex

        assert _resolvable_account_name(f"{domain}\\{name}") == f"{domain}\\{name}"

    def test_Given_bare_name__Then_unchanged(self):
        name = uuid4().hex

        assert _resolvable_account_name(name) == name


class TestGrantServiceRights:
    def test_Given_grant_succeeds__Then_account_granted_and_zero(self, mocker: MockerFixture):
        account = f".\\{uuid4().hex}"
        grant_mock = mocker.patch.object(grant_rights, grant_rights._grant_account_rights.__name__)  # noqa: SLF001 # patching the module-private grant helper to test the orchestration

        exit_code = grant_service_rights(account=account)

        assert exit_code == 0
        grant_mock.assert_called_once_with(account)

    def test_Given_grant_raises__Then_one(self, mocker: MockerFixture):
        account = f".\\{uuid4().hex}"
        error_message = str(uuid4())
        _ = mocker.patch.object(
            grant_rights,
            grant_rights._grant_account_rights.__name__,  # noqa: SLF001 # patching the module-private grant helper to test the orchestration
            side_effect=RuntimeError(error_message),
        )

        exit_code = grant_service_rights(account=account)

        assert exit_code == 1


class TestDispatchGrantRights:
    def test_Given_account_flag__Then_parsed_into_account_kwarg(self, mocker: MockerFixture):
        account = f".\\{uuid4().hex}"
        run_mock = mocker.patch.object(grant_rights, grant_rights.grant_service_rights.__name__, return_value=0)

        exit_code = dispatch_grant_rights(["--account", account])

        assert exit_code == 0
        run_mock.assert_called_once_with(account=account)
