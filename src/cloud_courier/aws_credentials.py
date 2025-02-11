import os
from pathlib import Path


def path_to_aws_credentials() -> Path:
    # https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent-technical-details.html
    if (
        os.name == "nt"
    ):  # pragma: no cover # In Linux test environments, pathlib throws an error trying to run this: cannot instantiate 'WindowsPath' on your system
        return Path("C:") / "Windows" / "System32" / "config" / "systemprofile" / ".aws" / "credentials"
    return (  # pragma: no cover # In Windows test environments, pathlib will probably throw an error about this
        Path("/var") / "lib" / "amazon" / "ssm" / "credentials"
    )
