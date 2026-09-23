<#
.SYNOPSIS
    Cook and package the GuildAccess mod headlessly.
.EXAMPLE
    tools\build-mod.ps1
.EXAMPLE
    tools\build-mod.ps1 -DevKit C:\ConanDevKit
#>
param(
    [string]$DevKit = 'C:\Program Files\Epic Games\CEUE5Devkit',

    [string]$Mod = 'GuildAccess'
)

$ErrorActionPreference = 'Stop'

$uat     = Join-Path $DevKit 'Engine\Build\BatchFiles\RunUAT.bat'
$project = Join-Path $DevKit 'UE4\ConanSandbox.uproject'
$scripts = Join-Path $DevKit 'UE4\'
$modSrc  = Join-Path $DevKit "UE4\Content\Mods\$Mod"
$output  = Join-Path $DevKit "UE4\Saved\Mods\$Mod\Output\$Mod.pak"

foreach ($p in @($uat, $project)) {
    if (-not (Test-Path $p)) {
        throw "Not found: $p`nIs -DevKit correct? See docs\PHASE-0-SETUP.md"
    }
}

if (-not (Test-Path $modSrc)) {
    throw "Mod folder not found: $modSrc`nCreate the '$Mod' mod in the dev kit first (Phase 0 step 4)."
}

Write-Host "Building $Mod from $modSrc" -ForegroundColor Cyan
$started = Get-Date

& $uat -NoCompile BuildMod -Mod=$Mod -Project="$project" -Cook -Pak -Compress -ScriptDir="$scripts"

if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host "BuildMod failed with exit code $LASTEXITCODE." -ForegroundColor Red
    Write-Host "Scroll up to the FIRST error in the UAT log, not the last - the tail is usually just teardown noise." -ForegroundColor Yellow
    Write-Host "If the error mentions paths, filenames, or 'path too long', see docs\PHASE-0-SETUP.md section 1 for the junction workaround." -ForegroundColor Yellow
    throw "BuildMod failed."
}

if (-not (Test-Path $output)) {
    throw "BuildMod reported success but no .pak at $output"
}

$size = [math]::Round((Get-Item $output).Length / 1MB, 2)
$mins = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
Write-Host "OK  $output  ($size MB, $mins min)" -ForegroundColor Green
