# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-base-template.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UV_VERSION = "0.12.15"
PNPM_VERSION = "12.4.2"
COPIER_VERSION = "==9.18.2"
COPIER_TEMPLATE_EXTENSIONS_VERSION = "==0.3.3"
PRE_COMMIT_VERSION = "4.6.2"
TASK_VERSION = "3.53.1"
DOWNLOAD_TIMEOUT_SECONDS = 90
# Where both uv's and Task's installers place binaries. Resolves from USERPROFILE on Windows, so it
# matches the runner's home directory without assuming its user name. Already on PATH on POSIX, but
# not on Windows, which is why uv is invoked through an absolute path there.
LOCAL_BIN_DIR = Path.home() / ".local" / "bin"
INSTALL_SSM_PLUGIN_BY_DEFAULT = False
parser = argparse.ArgumentParser(description="Install CI tooling for the repo")
_ = parser.add_argument(
    "--no-python",
    default=False,
    action="store_true",
    help="Do not process any environments using python package managers",
)
_ = parser.add_argument(
    "--python-version",
    default=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    type=str,
    help="What version to install.",
)
_ = parser.add_argument(
    "--no-node", action="store_true", default=False, help="Do not process any environments using node package managers"
)
_ = parser.add_argument(
    "--skip-installing-ssm-plugin",
    action="store_true",
    default=False,
    help="Skip installing the SSM plugin for AWS CLI",
)


def pwsh_cmd(cmd: str) -> list[str]:
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        raise FileNotFoundError("Neither 'pwsh' nor 'powershell' found on PATH")
    return [pwsh, "-NoProfile", "-NonInteractive", "-Command", cmd]


def install_task(*, is_windows: bool) -> None:
    """Install the pinned Task release into `LOCAL_BIN_DIR`.

    Deliberately not `npm install -g @go-task/cli`: that writes to the global prefix of whichever
    node is on PATH, and in CI that is the pnpm-managed node installed by `pnpm/setup`, whose prefix
    bin directory is not the one on PATH. The package installs successfully and the linked
    executable is then unreachable, so `task` fails with exit status 127.

    Verification goes through the absolute path because this process resolved PATH before the
    install; `GITHUB_PATH` is appended so later steps in the same CI job can invoke `task` by name.
    """
    LOCAL_BIN_DIR.mkdir(parents=True, exist_ok=True)
    if is_windows:
        if platform.machine().lower() == "arm64":
            windows_arch = "arm64"
        else:
            windows_arch = "amd64"
        archive_url = (
            f"https://github.com/go-task/task/releases/download/v{TASK_VERSION}/task_windows_{windows_arch}.zip"
        )
        # The bin directory is handed over as an environment variable rather than interpolated into the
        # script text: PowerShell single quotes take no escapes, so an apostrophe in the home directory
        # would terminate the string early. A variable reference is one argument whatever it contains.
        task_env = dict(os.environ)
        task_env.update({"TASK_BIN_DIR": str(LOCAL_BIN_DIR)})
        powershell_statements = [
            "$ErrorActionPreference = 'Stop'",
            "$archive = Join-Path $env:TEMP 'task-release.zip'",
            f"Invoke-WebRequest -UseBasicParsing -Uri '{archive_url}' -OutFile $archive",
            "Expand-Archive -Path $archive -DestinationPath $env:TASK_BIN_DIR -Force",
            "Remove-Item $archive",
        ]
        _ = subprocess.run(  # noqa: S603 # this is all our own input
            pwsh_cmd("; ".join(powershell_statements)),
            check=True,
            env=task_env,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
        task_path = LOCAL_BIN_DIR / "task.exe"
    else:
        # The installer resolves the pinned tag against the published checksums, so the archive is verified.
        # The bin directory is shell-quoted because a space or apostrophe in the home directory would
        # otherwise split it into multiple arguments, or unbalance the quoting outright.
        _ = subprocess.run(  # noqa: S602 # we need to set shell to true to use the pipe operator, and this is all our own input
            f"curl -fsSL --connect-timeout 20 --max-time 40 --retry 3 --retry-delay 5 --retry-connrefused --proto '=https' https://taskfile.dev/install.sh | sh -s -- -b {shlex.quote(str(LOCAL_BIN_DIR))} v{TASK_VERSION}",
            check=True,
            shell=True,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
        task_path = LOCAL_BIN_DIR / "task"
    _ = subprocess.run([str(task_path), "--version"], check=True)  # noqa: S603 # this is all our own input
    if "GITHUB_PATH" in os.environ:
        with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as github_path_file:
            _ = github_path_file.write(f"{LOCAL_BIN_DIR}\n")


def run_node_cmds(cmds: list[str], *, is_windows: bool) -> None:
    for cmd in cmds:
        if is_windows:
            run_cmd = pwsh_cmd(cmd)
        else:
            run_cmd = [cmd]
        _ = subprocess.run(run_cmd, shell=True, check=True, timeout=DOWNLOAD_TIMEOUT_SECONDS)  # noqa: S602 # we need shell=True for npm commands, and this is all our own input


def main():
    args = parser.parse_args(sys.argv[1:])
    is_windows = platform.system() == "Windows"
    uv_env = dict(os.environ)
    uv_env.update({"UV_PYTHON": args.python_version, "UV_PYTHON_PREFERENCE": "only-system"})
    if is_windows:
        uv_path = str(LOCAL_BIN_DIR / "uv")
    else:
        uv_path = "uv"
    if not args.no_python:
        if is_windows:
            uv_env.update({"PATH": rf"{LOCAL_BIN_DIR};{uv_env['PATH']}"})
            _ = subprocess.run(  # noqa: S603 # this is all our own input
                pwsh_cmd(f"irm https://astral.sh/uv/{UV_VERSION}/install.ps1 | iex"),
                check=True,
                env=uv_env,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
        else:
            _ = subprocess.run(  # noqa: S602 # we need to set shell to true to use the pipe operator, and this is all our own input
                f"curl -fsSL --connect-timeout 20 --max-time 40 --retry 3 --retry-delay 5 --retry-connrefused --proto '=https' https://astral.sh/uv/{UV_VERSION}/install.sh | sh",
                check=True,
                shell=True,
                env=uv_env,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            )
            # TODO: add uv autocompletion to the shell https://docs.astral.sh/uv/getting-started/installation/#shell-autocompletion
        _ = subprocess.run(  # noqa: S603 # this is all our own input
            [
                uv_path,
                "tool",
                "install",
                f"copier{COPIER_VERSION}",
                "--with",
                f"copier-template-extensions{COPIER_TEMPLATE_EXTENSIONS_VERSION}",
            ],
            check=True,
            env=uv_env,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
        _ = subprocess.run(  # noqa: S603 # this is all our own input
            [
                uv_path,
                "tool",
                "install",
                f"pre-commit=={PRE_COMMIT_VERSION}",
            ],
            check=True,
            env=uv_env,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
        )
        _ = subprocess.run(  # noqa: S603 # this is all our own input
            [
                uv_path,
                "tool",
                "list",
            ],
            check=True,
            env=uv_env,
        )
    if not args.no_node:
        run_node_cmds(["npm -v", f"npm install -g pnpm@{PNPM_VERSION}", "pnpm -v"], is_windows=is_windows)
    # Task is installed outside the --no-node branch because CI always passes --no-node (pnpm/setup handles pnpm there), and every job still needs the task runner
    install_task(is_windows=is_windows)
    if INSTALL_SSM_PLUGIN_BY_DEFAULT and not args.skip_installing_ssm_plugin:
        with tempfile.TemporaryDirectory() as tmp_dir:
            if is_windows:
                local_package_path = Path(tmp_dir) / "SessionManagerPluginSetup.exe"
                # Based on https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-windows.html
                # no specific reason for that version, just pinning it for best practice
                _ = subprocess.run(  # noqa: S603 # this is all our own input
                    [  # noqa: S607 # curl should always be on PATH
                        "curl",
                        "https://s3.amazonaws.com/session-manager-downloads/plugin/1.2.707.0/windows/SessionManagerPluginSetup.exe",
                        "-o",
                        f"{local_package_path}",
                    ],
                    check=True,
                    timeout=DOWNLOAD_TIMEOUT_SECONDS,
                )
                _ = subprocess.run(  # noqa: S603 # this is all our own input
                    [str(local_package_path), "/quiet"],
                    check=True,
                )
            else:
                local_package_path = Path(tmp_dir) / "session-manager-plugin.deb"
                # Based on https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian-and-ubuntu.html
                # no specific reason for that version, just pinning it for best practice
                _ = subprocess.run(  # noqa: S603 # this is all our own input
                    [  # noqa: S607 # curl should always be on PATH
                        "curl",
                        "https://s3.amazonaws.com/session-manager-downloads/plugin/1.2.707.0/ubuntu_64bit/session-manager-plugin.deb",
                        "-o",
                        f"{local_package_path}",
                    ],
                    check=True,
                    timeout=DOWNLOAD_TIMEOUT_SECONDS,
                )
                _ = subprocess.run(  # noqa: S603 # this is all our own input
                    [  # noqa: S607 # sudo should always be on PATH
                        "sudo",
                        "dpkg",
                        "-i",
                        str(local_package_path),
                    ],
                    check=True,
                )
            print("SSM Plugin Manager Version: ")  # noqa: T201 # we want the script to print to console for easy viewing
            _ = subprocess.run(
                [  # noqa: S607 # session-manager-plugin should be on PATH because we just installed it
                    "session-manager-plugin",
                    "--version",
                ],
                check=True,
            )


if __name__ == "__main__":
    main()
