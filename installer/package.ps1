# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
<#
.SYNOPSIS
    Packages the Cloud Courier MSI installer.

.DESCRIPTION
    Orchestrates the full packaging run:
      1. Stage artifacts (frontend + PyInstaller bundle + install scripts)
      2. Compile the MSI from wix/Product.wxs (WixUI account dialog + launch)

    Output: dist/CloudCourier-<version>.msi

.PARAMETER Version
    Override version. Defaults to [project].version in backend/pyproject.toml.

.PARAMETER SkipStage
    Reuse the existing build/staging tree (iterate on WiX without re-staging the
    bundle every time).

.PARAMETER Sign
    Code-sign the exe (before it is harvested into the MSI) and the final
    MSI via Azure Trusted Signing (the dotnet `sign` tool). Requires an Azure
    credential in the environment with the "Trusted Signing Certificate Profile
    Signer" role - locally via `az login`, in CI via azure/login.
#>
[CmdletBinding()]
param(
    [string] $Version,
    [switch] $SkipStage,
    [switch] $Sign,
    [string] $SigningAccount = '',
    [string] $SigningProfile = '',
    [string] $SigningEndpoint = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Read-PyprojectVersion {
    param([string]$PyprojectPath)
    if (-not (Test-Path $PyprojectPath)) { throw "pyproject.toml not found at $PyprojectPath" }
    $content = Get-Content $PyprojectPath -Raw
    $inProject = $false
    foreach ($line in $content -split "`n") {
        $trim = $line.Trim()
        if ($trim -match '^\[project\]\s*$') { $inProject = $true; continue }
        if ($trim -match '^\[' -and $inProject) { break }
        if ($inProject -and $trim -match '^version\s*=\s*"([^"]+)"') { return $matches[1] }
    }
    throw "Could not read [project].version from $PyprojectPath"
}

function Invoke-CodeSign {
    param([string]$BaseDir, [string]$Pattern)
    Write-Host "  signing $Pattern (Azure Trusted Signing)" -ForegroundColor DarkGray
    & sign code trusted-signing -b $BaseDir -tse $SigningEndpoint -tscp $SigningProfile -tsa $SigningAccount $Pattern -v Information
    if ($LASTEXITCODE -ne 0) { throw "code signing failed for $Pattern" }
}

function Test-Tool {
    param([string]$Name, [string]$Command, [string]$InstallHint)
    Write-Host "  checking $Name ... " -NoNewline
    try {
        $null = & $Command --version 2>&1
        Write-Host "ok" -ForegroundColor Green
    } catch {
        Write-Host "missing" -ForegroundColor Red
        throw "$Name not found on PATH. $InstallHint"
    }
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BuildDir = Join-Path $ScriptRoot 'build'
$StagingDir = Join-Path $BuildDir 'staging'
$DistDir = Join-Path $ScriptRoot 'dist'
$WixDir = Join-Path $ScriptRoot 'wix'
# Directory (relative to the repo root) holding the installer icon; it must contain favicon.ico.
# Frontend apps reuse frontend/public; apps without a frontend point this elsewhere (e.g. installer/).
$BrandingDir = Join-Path $RepoRoot 'frontend\public'
$LicenseRtf = Join-Path $ScriptRoot 'license.rtf'

if (-not $Version) {
    $Version = Read-PyprojectVersion -PyprojectPath (Join-Path $RepoRoot 'backend\pyproject.toml')
}

Write-Host "Cloud Courier installer build" -ForegroundColor Cyan
Write-Host "  Version   : $Version"
Write-Host "  SkipStage : $SkipStage"
Write-Host ""

Write-Host "Tool check" -ForegroundColor Cyan
Test-Tool 'wix'    'wix'    'Install with: dotnet tool install --global wix'
Test-Tool 'dotnet' 'dotnet' 'Install .NET SDK 8.0+'
Write-Host ""

Write-Host "Ensuring WiX extensions" -ForegroundColor Cyan
$wixVersion = (wix --version 2>&1).Trim()
if (-not $wixVersion) { throw "Could not read wix CLI version" }
Write-Host "  wix CLI : $wixVersion"
# Pin extensions to the exact CLI version (strip any +build metadata) so they
# never drift from the toolset the workflow installed.
$wixSemVer = ($wixVersion -split '\+')[0]
$wixMajor = ($wixVersion -split '\.')[0]
if ([int]$wixMajor -ge 7) {
    Write-Host "  Accepting WiX v$wixMajor EULA" -ForegroundColor DarkGray
    wix eula accept "wix$wixMajor" 2>&1 | Out-Null
}
foreach ($ext in @('WixToolset.Util.wixext', 'WixToolset.UI.wixext')) {
    Write-Host "  $ext ... " -NoNewline
    $existing = wix extension list -g 2>&1 | Select-String "$ext $wixSemVer"
    if ($existing) { Write-Host "present" -ForegroundColor Green; continue }
    wix extension add -g "$ext/$wixSemVer"
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED" -ForegroundColor Red; throw "wix extension add failed for $ext" }
    Write-Host "added" -ForegroundColor Yellow
}
Write-Host ""

if ($Sign) {
    Write-Host "Code signing enabled (Azure Trusted Signing)" -ForegroundColor Cyan
    if (-not (Get-Command sign -ErrorAction SilentlyContinue)) {
        Write-Host "  installing sign tool" -ForegroundColor DarkGray
        dotnet tool install --global --prerelease sign 2>&1 | Out-Null
        $env:PATH = "$env:USERPROFILE\.dotnet\tools;$env:PATH"
    }
    Write-Host ""
}

if (-not $SkipStage) {
    Write-Host "Staging artifacts" -ForegroundColor Cyan
    # stage.ps1 is a PowerShell script, not a native command: it signals failure by
    # throwing, which $ErrorActionPreference = 'Stop' already propagates. $LASTEXITCODE
    # here would hold the last *native* command's code (e.g. wix extension add), not
    # stage.ps1's result, so checking it is misleading — rely on the thrown exception.
    & (Join-Path $ScriptRoot 'stage.ps1') -StagingDir $StagingDir -RepoRoot $RepoRoot
} else {
    Write-Host "Skipping stage (using existing $StagingDir)" -ForegroundColor Yellow
    if (-not (Test-Path $StagingDir)) { throw "-SkipStage set but $StagingDir does not exist" }
    Write-Host "  Syncing scripts/ -> staging" -ForegroundColor DarkGray
    if (Test-Path (Join-Path $StagingDir 'scripts')) { Remove-Item -Recurse -Force (Join-Path $StagingDir 'scripts') }
    Copy-Item -Recurse -Path (Join-Path $ScriptRoot 'scripts') -Destination (Join-Path $StagingDir 'scripts')
}
Write-Host ""

if ($Sign) {
    Write-Host "Signing app binaries" -ForegroundColor Cyan
    # Sign the bundled native modules (PyInstaller's _internal\ .dll/.pyd) as well as
    # the exe, so every executable payload in the bundle is signed, not just the entry.
    $AppDir = Join-Path $StagingDir 'app'
    Invoke-CodeSign -BaseDir $AppDir -Pattern '**/*.dll'
    Invoke-CodeSign -BaseDir $AppDir -Pattern '**/*.pyd'
    Invoke-CodeSign -BaseDir $AppDir -Pattern 'cloud-courier.exe'
    Write-Host ""
}

New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

Write-Host "Compiling MSI" -ForegroundColor Cyan
$MsiOut = Join-Path $DistDir "CloudCourier-$Version.msi"
$MsiArgs = @(
    'build',
    '-arch', 'x64',
    '-define', "ProductVersion=$Version",
    '-define', "StagingDir=$StagingDir",
    '-define', "BrandingDir=$BrandingDir",
    '-define', "LicenseRtf=$LicenseRtf",
    '-ext', 'WixToolset.Util.wixext',
    '-ext', 'WixToolset.UI.wixext',
    '-out', $MsiOut,
    # Keep build metadata out of the ship dir; only the .msi belongs in dist/.
    '-pdb', (Join-Path $BuildDir "CloudCourier-$Version.wixpdb"),
    (Join-Path $WixDir 'Product.wxs')
)
& wix @MsiArgs
if ($LASTEXITCODE -ne 0) { throw "wix build (MSI) failed" }
Write-Host ""

if ($Sign) {
    Write-Host "Signing MSI" -ForegroundColor Cyan
    Invoke-CodeSign -BaseDir $DistDir -Pattern "CloudCourier-$Version.msi"
    Write-Host ""
}

# Ship the end-user install guide alongside the MSI.
Copy-Item -Force -Path (Join-Path $ScriptRoot 'INSTALL.txt') -Destination (Join-Path $DistDir 'INSTALL.txt')

Write-Host "Done." -ForegroundColor Green
Write-Host "  Installer : $MsiOut"
Write-Host "  Guide     : $(Join-Path $DistDir 'INSTALL.txt')"
