<#
.SYNOPSIS
    Replace the dev kit's mod folder with a junction into this repo, so git
    tracks the real assets. Idempotent and safe to re-run (e.g. after a dev kit
    update wipes the link).
.EXAMPLE
    tools\link-mod.ps1
#>
param(
    [string]$DevKit = 'C:\Program Files\Epic Games\CEUE5Devkit',
    [string]$Repo   = 'E:\ClaudeCode\conan-exiles\guild-access',
    [string]$Mod    = 'GuildAccess'
)

$ErrorActionPreference = 'Stop'

$devkitMod = Join-Path $DevKit "UE4\Content\Mods\$Mod"
$repoMod   = Join-Path $Repo $Mod

if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    throw "The dev kit editor is running. Close it first - it holds file locks on the mod folder."
}

if (-not (Test-Path (Join-Path $DevKit 'UE4\Content\Mods'))) {
    throw "No Mods folder at $DevKit. Create the '$Mod' mod in the dev kit first."
}

$existing = Get-Item $devkitMod -Force -ErrorAction SilentlyContinue

if ($existing -and $existing.LinkType -eq 'Junction') {
    Write-Host "Already linked: $devkitMod -> $($existing.Target)" -ForegroundColor Green
    exit 0
}

if ($existing -and (Test-Path $repoMod)) {
    throw "Both $devkitMod and $repoMod exist as real folders. Resolve by hand - I will not guess which one has your work."
}

if ($existing) {
    Write-Host "Moving $devkitMod -> $repoMod"
    Move-Item -Path $devkitMod -Destination $repoMod
}

if (-not (Test-Path $repoMod)) {
    throw "Nothing to link: $repoMod does not exist and there was no dev kit folder to move."
}

Write-Host "Creating junction $devkitMod -> $repoMod"
New-Item -ItemType Junction -Path $devkitMod -Target $repoMod | Out-Null

$check = Get-Item $devkitMod -Force
if ($check.LinkType -ne 'Junction') {
    throw "Junction creation reported success but $devkitMod is not a junction."
}

Write-Host "OK  $devkitMod -> $($check.Target)" -ForegroundColor Green
Write-Host "Verifying the dev kit can see the contents..."
Get-ChildItem $devkitMod | Select-Object Name | Format-Table -HideTableHeaders
