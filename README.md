[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
[![Actions status](https://github.com/LabAutomationAndScreening/cloud-courier/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/LabAutomationAndScreening/cloud-courier/actions)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/LabAutomationAndScreening/cloud-courier)[![Codecov](https://codecov.io/gh/LabAutomationAndScreening/cloud-courier/branch/main/graph/badge.svg)](https://codecov.io/gh/LabAutomationAndScreening/cloud-courier)
[![Documentation Status](https://readthedocs.org/projects/cloud-courier/badge/?version=latest)](https://cloud-courier.readthedocs.io/en/latest/?badge=latest)

# Usage
Documentation is hosted on [ReadTheDocs](https://cloud-courier.readthedocs.io/en/latest/?badge=latest).

# Development
This project has a dev container. If you already have VS Code and Docker installed, you can click the badge above or [here](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/LabAutomationAndScreening/cloud-courier) to get started. Clicking these links will cause VS Code to automatically install the Dev Containers extension if needed, clone the source code into a container volume, and spin up a dev container for use.

To publish a new version of the repository, you can run the `Publish` workflow manually and publish to the staging registry from any branch, and you can check the 'Publish to Primary' option when on `main` to publish to the primary registry and create a git tag.





## Updating from the template
This repository uses a copier template. To pull in the latest updates from the template, use the command:
`copier update --trust --conflict rej --defaults`
