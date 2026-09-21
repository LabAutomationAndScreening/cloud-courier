# ============== WARNING ==============================================================================
# File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
# See .config/.copier-managed-files.json for details.
#
# You are welcome to make changes to this file in your repo if they are custom to your project,
# but if the change should be shared with other projects, please backport it to the template repo.
# =====================================================================================================
<#
.SYNOPSIS
    Stops and unregisters the Cloud Courier Windows service. Run by the MSI
    as a deferred (elevated, SYSTEM) custom action on uninstall, before files are
    removed.

.DESCRIPTION
    Mirror of install-service.ps1: uses the exe's own `service stop` / `service
    remove` verbs. Best-effort - a missing or already-stopped service must not
    fail the uninstall, so failures are swallowed.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $ExePath
)

Set-StrictMode -Version Latest

$ServiceName = 'LabAutomationAndScreening-cloud-courier'

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Host "Stopping service $ServiceName"
    & $ExePath service stop 2>&1 | Out-Null

    Write-Host "Removing service $ServiceName"
    & $ExePath service remove 2>&1 | Out-Null
} else {
    Write-Host "Service $ServiceName not present; nothing to remove"
}

# Remove the inbound firewall rule install-service.ps1 may have created (no-op if absent).
# Best-effort: surface a real removal failure but never fail the uninstall (see .DESCRIPTION).
$firewallRule = Get-NetFirewallRule -DisplayName "$ServiceName (HTTP-In)" -ErrorAction SilentlyContinue
if ($firewallRule) {
    try {
        $firewallRule | Remove-NetFirewallRule -ErrorAction Stop
    } catch {
        Write-Warning "Failed to remove firewall rule '$ServiceName (HTTP-In)' during uninstall: $_"
    }
}

exit 0
