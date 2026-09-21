# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
<#
.SYNOPSIS
    Stages the Cloud Courier build artifacts for the WiX MSI.

.DESCRIPTION
    Stages the prebuilt backend/dist/cloud-courier bundle and arranges everything
    into $StagingDir in the layout the MSI harvest expects:

      app/        cloud-courier.exe + _internal/ (the PyInstaller bundle)
      scripts/    install-time PowerShell helpers (service lifecycle)

    The bundle must already exist (downloaded from the CI run that produced and
    tested it), so the shipped MSI wraps the exact tested binary. This script
    never rebuilds the app itself.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $StagingDir,
    [Parameter(Mandatory)] [string] $RepoRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RepoRoot 'backend'
$DistDir = Join-Path $BackendDir 'dist\cloud-courier'

if (Test-Path $StagingDir) {
    Remove-Item -Recurse -Force $StagingDir
}
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

Write-Host "  Staging existing $DistDir" -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $DistDir 'cloud-courier.exe'))) {
    throw "$DistDir\cloud-courier.exe not found - download the tested bundle into $DistDir first."
}

Write-Host "  Arranging staging tree" -ForegroundColor Cyan
$AppStaging = Join-Path $StagingDir 'app'
Copy-Item -Recurse -Force -Path $DistDir -Destination $AppStaging
Copy-Item -Recurse -Force -Path (Join-Path $ScriptRoot 'scripts') -Destination (Join-Path $StagingDir 'scripts')

Write-Host "  Done. Staging at $StagingDir" -ForegroundColor Green
