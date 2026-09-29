# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
<#
.SYNOPSIS
    Registers and starts the Cloud Courier Windows service. Run by the MSI
    as a deferred (elevated, SYSTEM) custom action after files are installed.

.DESCRIPTION
    The exe is SCM-compliant (pywin32), so the service is registered by invoking
    the exe's own `service install` verb rather than a native WiX ServiceInstall.
    This keeps the exe inside the file harvest and lets the account choice
    (LocalSystem vs a supplied low-privilege account) live in one place.

    For a custom account the script also grants that account the rights it needs
    (Log on as a service, plus any app-specific privileges, via the exe's
    grant-service-rights verb) and Modify on the writable data dir, since a
    session-0 service cannot prompt for elevation at runtime.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $ExePath,
    [Parameter(Mandatory)] [string] $Port,
    [Parameter(Mandatory)] [string] $LogDir,
    [string] $ServiceAccount = 'LocalSystem',
    [string] $User = '',
    [string] $Password = '',
    # '1' => bind 0.0.0.0 (reachable from other computers), anything else => 127.0.0.1.
    [string] $AllowRemote = '0'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ServiceName = 'LabAutomationAndScreening-cloud-courier'

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$installArgs = @('service')

if ($ServiceAccount -ieq 'custom') {
    if ([string]::IsNullOrWhiteSpace($User)) {
        throw "A custom service account was selected but no user name was supplied."
    }
    if ([string]::IsNullOrWhiteSpace($Password)) {
        throw "A custom service account was selected but no password was supplied."
    }
    $account = if ($User.Contains('\')) { $User } else { ".\$User" }
    # LookupAccountName and icacls cannot resolve the ".\" logon shorthand; strip it for them.
    # SCM still wants the ".\name" form for --username.
    $rightsAccount = if ($account.StartsWith('.\')) { $account.Substring(2) } else { $account }

    Write-Host "Granting service rights to $rightsAccount"
    & $ExePath grant-service-rights --account $rightsAccount
    if ($LASTEXITCODE -ne 0) { throw "grant-service-rights failed for $rightsAccount" }

    Write-Host "Granting $rightsAccount Modify on $LogDir"
    & icacls $LogDir /grant "${rightsAccount}:(OI)(CI)M" /T | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls failed to grant Modify on $LogDir for $rightsAccount (exit $LASTEXITCODE)" }

    # The password is NOT passed on the command line: the exe's process command line is
    # readable by any local process (Win32_Process) for the install window. It travels via
    # an environment variable instead, which win_service.py reads and splices into pywin32's
    # in-memory HandleCommandLine arg list. The var name must match SERVICE_INSTALL_PASSWORD_ENV
    # in backend_api.entrypoint.service_install_password.
    $installArgs += @('--username', $account)
    $env:WINDOWS_SERVICE_INSTALL_PASSWORD = $Password
}

$installArgs += @('--startup', 'auto', 'install', '--', '--port', $Port, '--log-folder', $LogDir)

# Operator-selected bind address (see the installer's network-access page / ALLOW_REMOTE property).
$bindHost = if ($AllowRemote -eq '1') { '0.0.0.0' } else { '127.0.0.1' }
$installArgs += @('--host', $bindHost)


# $installArgs no longer carries the password, so it is safe to log verbatim.
Write-Host "Installing service: $ExePath $($installArgs -join ' ')"
try {
    & $ExePath @installArgs
}
finally {
    Remove-Item Env:\WINDOWS_SERVICE_INSTALL_PASSWORD -ErrorAction SilentlyContinue
}
if ($LASTEXITCODE -ne 0) { throw "Service install failed (exit $LASTEXITCODE)" }

# Windows Firewall: open the service port for remote access, scoped to this exe and the local
# subnet. The template opens only the single defined port; apps that need more (extra ports,
# UDP/mDNS, etc.) add their own rules. Rebuilt idempotently so toggling remote access off removes it.
$FirewallRuleName = "$ServiceName (HTTP-In)"
# Abort the install if a stale rule exists but cannot be removed: recreating over it would
# leave a duplicate or wrongly-scoped rule. A missing rule is fine (nothing to remove).
$existingFirewallRule = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
if ($existingFirewallRule) {
    try {
        $existingFirewallRule | Remove-NetFirewallRule -ErrorAction Stop
    } catch {
        throw "Failed to remove existing firewall rule '$FirewallRuleName': $_"
    }
}
$openFirewall = ($AllowRemote -eq '1')
if ($openFirewall) {
    Write-Host "Opening firewall rule '$FirewallRuleName' (TCP $Port, LocalSubnet)"
    $null = New-NetFirewallRule -DisplayName $FirewallRuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress LocalSubnet -Program $ExePath
}

Write-Host "Starting service $ServiceName"
Start-Service -Name $ServiceName

Write-Host "install-service.ps1 complete"
exit 0
