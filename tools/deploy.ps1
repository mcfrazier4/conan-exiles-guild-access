<#
.SYNOPSIS
    Build the mod and install it to both the game client and the local
    dedicated server. The Phase 2 iteration loop.
.EXAMPLE
    tools\deploy.ps1
.EXAMPLE
    tools\deploy.ps1 -SkipBuild      # reinstall the existing .pak
.NOTES
    Close the dev kit editor first - cooking conflicts with it.
    Stop the dedicated server first - it holds a lock on the extracted mod.
#>
param(
    [string]$DevKit = 'C:\Program Files\Epic Games\CEUE5Devkit',
    [string]$Client = 'C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles',
    [string]$Server = 'C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles Dedicated Server',
    [string]$Stage  = 'C:\ConanMods',
    [string]$Mod    = 'GuildAccess',
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot 'build-mod.ps1') -DevKit $DevKit -Mod $Mod
    if ($LASTEXITCODE -ne 0) { throw "Build failed; nothing deployed." }
}

$pak = Join-Path $DevKit "UE4\Saved\Mods\$Mod\Output\$Mod.pak"
if (-not (Test-Path $pak)) { throw "No .pak at $pak" }

if (-not (Test-Path $Stage)) { New-Item -ItemType Directory -Path $Stage -Force | Out-Null }
$staged = Join-Path $Stage "$Mod.pak"
Copy-Item $pak $staged -Force
Write-Host "Staged $staged ($([math]::Round((Get-Item $staged).Length/1KB)) KB)" -ForegroundColor Cyan

function Set-ModList {
    param([string]$Root, [string]$Label)

    if (-not (Test-Path $Root)) { Write-Warning "$Label not found at $Root - skipped."; return }

    $modsDir = Join-Path $Root 'ConanSandbox\Mods'
    if (-not (Test-Path $modsDir)) { New-Item -ItemType Directory -Path $modsDir -Force | Out-Null }

    $list = Join-Path $modsDir 'modlist.txt'
    if (Test-Path $list) {
        # Keep every other entry, but disabled. Our line is the only active one.
        $kept = Get-Content $list | Where-Object { $_ -notmatch [regex]::Escape($staged) } |
                ForEach-Object { if ($_.Trim() -and $_ -notmatch '^#') { "#$_" } else { $_ } }
    } else {
        $kept = @()
    }
    Set-Content -Path $list -Value (@($kept) + $staged) -Encoding utf8
    Write-Host "  $Label modlist -> $list" -ForegroundColor Green
}

Set-ModList -Root $Client -Label 'Client'
Set-ModList -Root $Server -Label 'Server'

# The server caches an extracted copy; stale extracts silently run old code.
$extracted = Join-Path $Server 'ConanSandbox\Saved\ExtractedMods'
if (Test-Path $extracted) {
    Remove-Item (Join-Path $extracted "$Mod-*") -Force -ErrorAction SilentlyContinue
    Write-Host "  Cleared stale server ExtractedMods" -ForegroundColor Green
}
$extractedC = Join-Path $Client 'ConanSandbox\Saved\ExtractedMods'
if (Test-Path $extractedC) {
    Remove-Item (Join-Path $extractedC "$Mod-*") -Force -ErrorAction SilentlyContinue
    Write-Host "  Cleared stale client ExtractedMods" -ForegroundColor Green
}

Write-Host ''
Write-Host "Deployed. Restart the server and the game client to pick it up." -ForegroundColor Cyan
