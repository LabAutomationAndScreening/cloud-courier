# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import secrets

import pytest
from backend_api.entrypoint.service_install_password import SERVICE_INSTALL_PASSWORD_ENV
from backend_api.entrypoint.service_install_password import inject_install_password


def test_Given_no_password_env_var__Then_args_unchanged():
    args = ["--username", ".\\svc", "--startup", "auto", "install"]

    assert inject_install_password(args, env={}) == args


def test_Given_password_env_var__Then_spliced_before_install_subcommand():
    # pywin32 uses POSIX getopt, so options must come before the subcommand.
    expected_password = secrets.token_hex(16)
    args = ["--username", ".\\svc", "--startup", "auto", "install"]

    result = inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: expected_password})

    assert result == ["--username", ".\\svc", "--startup", "auto", "--password", expected_password, "install"]


def test_Given_username_value_equals_install__Then_password_spliced_before_the_subcommand():
    # The terminal token is the real subcommand; a --username value of "install" must not be
    # mistaken for it.
    expected_password = secrets.token_hex(16)
    args = ["--username", "install", "--startup", "auto", "install"]

    result = inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: expected_password})

    assert result == ["--username", "install", "--startup", "auto", "--password", expected_password, "install"]


@pytest.mark.parametrize("verb", ["start", "stop", "remove", "debug"])
def test_Given_non_install_subcommand__Then_password_not_injected(verb: str):
    args = [verb]

    assert inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: "s3cret"}) == args


def test_Given_empty_password__Then_treated_as_unset():
    args = ["install"]

    assert inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: ""}) == args


def test_Given_password_already_present__Then_not_duplicated():
    args = ["--username", ".\\svc", "--password", "already", "install"]

    assert inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: "s3cret"}) == args


def test_Given_env_omitted__Then_process_environment_is_used(monkeypatch: pytest.MonkeyPatch):
    # When env is not passed, the default branch reads os.environ.
    password = secrets.token_hex(16)
    monkeypatch.setenv(SERVICE_INSTALL_PASSWORD_ENV, password)
    args = ["install"]

    assert inject_install_password(args) == ["--password", password, "install"]


def test_Given_call__Then_input_list_not_mutated():
    args = ["install"]

    _ = inject_install_password(args, env={SERVICE_INSTALL_PASSWORD_ENV: "s3cret"})

    assert args == ["install"]
