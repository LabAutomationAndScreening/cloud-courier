[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Open in Dev Containers](https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://www.github.com/LabAutomationAndScreening/cloud-courier)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Checked with pyrefly](https://img.shields.io/endpoint?url=https://pyrefly.org/badge.json)](https://pyrefly.org/)
[![PNPM](https://img.shields.io/badge/pnpm-%234a4a4a.svg?style=flat&logo=pnpm&logoColor=f69220)](https://pnpm.io/)
[![Nuxtjs](https://img.shields.io/badge/Nuxt-002E3B?style=flat&logo=nuxtdotjs&logoColor=#00DC82)](https://nuxt.com/)
[![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)


# Development

Every multi-step workflow is defined as a [Task](https://taskfile.dev) task, so run `task --list` to see what is available. The definitions live in `.config/taskfiles/`; the root `Taskfile.yaml` only includes them.

To build and spin up the full stack (accessible on port 4000), run:
```bash
task run-stack
```
That generates the frontend, copies it into the backend static directory, builds the executable, and runs it.

To just rebuild the frontend and swap it into the already-built executable, run:
```bash
task reload-frontend-in-stack
```

## Frontend
Start the development server on `http://localhost:3000`:
```bash
task dev-frontend
```

Build the application for production:

```bash
task build-frontend
```

Locally preview production build:
```bash
task preview-frontend
```

## Backend
Start the API server on port 4000 (will not generate log files):
```bash
task dev-backend
```

Start the app using the entrypoint to be able to supply CLI options and log to file (running by default on port 4000):
```bash
task run-backend-entrypoint
```

## Codegen
To regenerate every generated client in this repo, run:

```bash
task codegen
```

That covers both sides of the app and all schema sources, refreshing the openapi.json snapshot before any client is generated from it. Run `task --list` for the individual tasks if you only need one of them. This is the only sanctioned way to update generated code: nothing under a `generated/` folder should ever be hand-edited.

## Updating from the template
This repository uses a copier template. To pull in the latest updates from the template, run `task copier-update`.

<!--
============== WARNING ==============================================================================
File is managed by copier template: gh:LabAutomationAndScreening/copier-base-template.git
See .config/.copier-managed-files.json for details.

You are welcome to make changes to this file in your repo if they are custom to your project,
but if the change should be shared with other projects, please backport it to the template repo.
=====================================================================================================
-->
