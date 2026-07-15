[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
[![Actions status](https://github.com/LabAutomationAndScreening/cloud-courier/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/LabAutomationAndScreening/cloud-courier/actions)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/LabAutomationAndScreening/cloud-courier)
[![Codecov](https://codecov.io/gh/LabAutomationAndScreening/cloud-courier/branch/main/graph/badge.svg)](https://codecov.io/gh/LabAutomationAndScreening/cloud-courier)
[![Documentation Status](https://readthedocs.org/projects/cloud-courier/badge/?version=latest)](https://cloud-courier.readthedocs.io/en/latest/?badge=latest)
[![OpenIssues](https://isitmaintained.com/badge/open/LabAutomationAndScreening/cloud-courier.svg)](https://isitmaintained.com/project/LabAutomationAndScreening/cloud-courier)

# Usage
Documentation is hosted on [ReadTheDocs](https://cloud-courier.readthedocs.io/en/latest/?badge=latest).

# Development
This project has a dev container. If you already have VS Code and Docker installed, you can click the badge above or [here](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/LabAutomationAndScreening/cloud-courier) to get started. Clicking these links will cause VS Code to automatically install the Dev Containers extension if needed, clone the source code into a container volume, and spin up a dev container for use.

The `Release` workflow reuses the checks from CI instead of re-running them: it requires that the `CI` workflow has already completed successfully for the current commit (including the `workflow-summary` job) and reuses the artifacts CI built rather than rebuilding. Trigger it manually with `workflow_dispatch`; a real release must be run from `main`, while the `dry_run` option lets you exercise the workflow from any branch without tagging or releasing. A real run pushes the `v<version>` git tag and creates a GitHub Release, attaching the executable that CI built for every OS and Python version.






## Updating from the template
This repository uses a copier template. To pull in the latest updates from the template, use the command:
`copier update --answers-file .config/.copier-answers.yml --trust --conflict rej --defaults`

<!--
============== WARNING ==============================================================================
File is managed by copier template: gh:LabAutomationAndScreening/copier-base-template.git
See .config/.copier-managed-files.json for details.

You are welcome to make changes to this file in your repo if they are custom to your project,
but if the change should be shared with other projects, please backport it to the template repo.
=====================================================================================================
-->
