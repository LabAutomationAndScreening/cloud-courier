# Installer Architecture

## Why this shape

Cloud Courier ships as a single PyInstaller one-folder bundle (`cloud-courier.exe` +
`_internal/`) that is SCM-compliant on its own (the exe implements the Windows service protocol via
pywin32).

## Build pipeline (`stage.ps1` -> `package.ps1`)

1. `stage.ps1` stages the prebuilt `backend/dist/cloud-courier/` bundle — copying it into
   `build/staging/app/` and the lifecycle scripts into `build/staging/scripts/`. The bundle must
   already exist.
2. `package.ps1` compiles `wix/Product.wxs` into the MSI (harvesting the staging tree). The MSI is
   the deliverable — a `WixUI_InstallDir` flow with a custom **Service account** dialog and a
   post-install "open the app" checkbox. No Burn bundle: there are no prerequisites to chain, and
   a plain MSI gives both an interactive dialog and clean silent install (`msiexec /qn` with the
   account/port set as properties).

`package.ps1` runs `stage.ps1` for you — you don't stage manually first. Pass `-SkipStage` to
reuse an existing `build/staging/` tree when iterating on WiX.

### Always consume the tested bundle

The installer never rebuilds the app — `stage.ps1` stages whatever bundle is already in
`backend/dist/cloud-courier/`. The reusable `build-installer.yaml` downloads that bundle (the one
the test suite ran against) so the MSI wraps the exact tested binary. To build locally, produce the
bundle first (`pnpm generate` + `pyinstaller`, or download a CI artifact) into
`backend/dist/cloud-courier/`, then run `package.ps1`. CI builds the MSI unsigned as a
build-breakage check; release builds + signs it from the guarded CI run's bundle, then zips
`CloudCourier-<version>.msi` + `INSTALL.txt` as the Windows release asset.

## Service registration

The MSI does **not** use a native `<ServiceInstall>`. Instead a deferred, elevated custom action
runs `scripts/install-service.ps1`, which calls the exe's own
`cloud-courier.exe service [...] install -- --port 4000 --log-folder <dir>` verb.
This is deliberate:

- It keeps `cloud-courier.exe` inside the `<Files>` harvest (a native `<ServiceInstall>` would need
  the exe declared in its own component, colliding with the harvest — WiX 7 `<Files>` has no
  Exclude).
- It reuses the app's own, tested install path (which bakes the runtime args into the service
  ImagePath).
- It puts the LocalSystem-vs-custom-account branching in one PowerShell script instead of
  conditional WiX components.

Uninstall mirrors this via `remove-service.ps1` (`service stop` + `service remove`).

## Service account

The **Service account** dialog offers two choices:

- **LocalSystem** (default). Runs with full local privileges; no credentials to manage.
- A **low-privilege account**. `install-service.ps1` grants it `Log on as a service` (plus any
  extra privileges configured via the template's `extra_windows_service_rights`) through the exe's
  `grant-service-rights` verb, and Modify on the writable data dir, because a session-0 service
  cannot prompt for elevation at runtime.

## Data layout

Binaries live under `Program Files\LabAutomationandSCreening\CloudCourier\`. The service log dir lives under
`ProgramData\LabAutomationandSCreening\CloudCourier\logs\` so it survives upgrades and is reachable by a
non-admin service account; the MSI ACLs it for SYSTEM/Administrators and `install-service.ps1` adds
Modify for a custom account at install time.

<!--
============== WARNING ==============================================================================
File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
See .config/.copier-managed-files.json for details.

You are welcome to make changes to this file in your repo if they are custom to your project,
but if the change should be shared with other projects, please backport it to the template repo.
=====================================================================================================
-->
