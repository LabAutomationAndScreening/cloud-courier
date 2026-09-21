# Cloud Courier Windows Installer

A WiX 7 MSI that packages Cloud Courier as a one-click Windows install: it lays down the
PyInstaller bundle and registers and starts the `LabAutomationAndScreening-cloud-courier` Windows service.

This README is the **build/dev** guide. For end-user install (interactive and silent) see
[`INSTALL.txt`](INSTALL.txt); for why the installer is shaped this way (build pipeline, service
registration, data layout) see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Output

`installer/dist/CloudCourier-<version>.msi` — installs the app and starts the service on
`http://127.0.0.1:4000`. Interactive installs offer an **Open Cloud Courier**
checkbox on the final page. `package.ps1` also copies `INSTALL.txt` into `dist/` to ship alongside the
MSI.

## Prerequisites (build machine)

- Windows x64
- [WiX 7 CLI](https://docs.firegiant.com/wix/): `dotnet tool install --global wix`
- .NET SDK 8.0+
- `uv`, `pnpm` (same tooling the app build uses)

## Build

```powershell
cd installer
./package.ps1
```

`package.ps1` checks tooling, ensures the required WiX extensions, stages artifacts via
`stage.ps1` (frontend build -> fold into backend static -> PyInstaller -> staging tree), then
compiles the MSI. Use `-SkipStage` to iterate on the WiX without rebuilding the app, and
`-Version <x.y.z>` to override the version (defaults to `backend/pyproject.toml`). See
[`ARCHITECTURE.md`](ARCHITECTURE.md) for the rebuild-vs-consume-the-tested-bundle split.

## Code signing

Pass `-Sign` to sign the app binaries (the exe plus the bundled `_internal\` DLLs/pyd) and
the final MSI via Azure Trusted Signing (the dotnet `sign` tool):

```powershell
./package.ps1 -Sign
```

Requires an Azure identity holding the **Trusted Signing Certificate Profile Signer** role on the
configured signing account — locally via `az login`, in CI via `azure/login`. Account / profile /
endpoint default to the values baked in at template time and can be overridden with
`-SigningAccount`, `-SigningProfile`, `-SigningEndpoint`.

CI (`.github/workflows/build-installer.yaml`) signs automatically when the `AZURE_CREDENTIALS` repo
secret is present (a service-principal JSON with that role); without it the build still produces an
unsigned MSI.

## Files

- `package.ps1` — packaging orchestrator (MSI).
- `stage.ps1` — produces the staging tree from the app build.
- `wix/Product.wxs` — the MSI: files, data dirs, the service-account dialog, service lifecycle
  custom actions, and the post-install launch.
- `scripts/install-service.ps1`, `scripts/remove-service.ps1` — invoked by the MSI's deferred
  custom actions to register/remove the service via the exe's `service ...` verbs.
- `license.rtf` — shown on the license page.
- `INSTALL.txt` — end-user/admin install guide; copied into `dist/` next to the MSI by `package.ps1`.

The installer icon reuses the app's own `frontend/public/favicon.ico`.

<!--
============== WARNING ==============================================================================
File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
See .config/.copier-managed-files.json for details.

You are welcome to make changes to this file in your repo if they are custom to your project,
but if the change should be shared with other projects, please backport it to the template repo.
=====================================================================================================
-->
