<#
.SYNOPSIS
    Cook and package the GuildAccess mod headlessly.
.EXAMPLE
    tools\build-mod.ps1
.EXAMPLE
    tools\build-mod.ps1 -DevKit C:\ConanDevKit -Verbose
.NOTES
    Two argument-passing traps, both learned the hard way (2026-09-23):

    1. Every "-Key=Value" argument MUST be quoted. PowerShell does not expand
       variables inside an unquoted token that starts with "-", so -Mod=$Mod
       reaches UAT as the literal string "-Mod=$Mod".

    2. Paths handed to UAT MUST use forward slashes. A trailing backslash before
       a closing quote escapes the quote, so -ScriptDir="...\UE4\" arrives as
       ...\UE4" and UAT reports "Specified ScriptDir doesn't exist".
#>
[CmdletBinding()]
param(
    [string]$DevKit = 'C:\Program Files\Epic Games\CEUE5Devkit',

    [string]$Mod = 'GuildAccess'
)

$ErrorActionPreference = 'Stop'

$uat     = Join-Path $DevKit 'Engine\Build\BatchFiles\RunUAT.bat'
$project = Join-Path $DevKit 'UE4\ConanSandbox.uproject'
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

if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    throw "The dev kit editor is running. Close it first - cooking conflicts with the editor holding the project open."
}

# Forward slashes, and no trailing slash on ScriptDir. See .NOTES above.
$projectArg   = $project.Replace('\', '/')
$scriptDirArg = (Join-Path $DevKit 'UE4').Replace('\', '/')

$uatArgs = @(
    '-NoCompile'
    'BuildMod'
    "-Mod=$Mod"
    "-Project=$projectArg"
    '-Cook'
    '-Pak'
    '-Compress'
    "-ScriptDir=$scriptDirArg"
)

Write-Host "Building $Mod from $modSrc" -ForegroundColor Cyan
Write-Verbose "UAT args: $($uatArgs -join ' ')"
$started = Get-Date

& $uat @uatArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host "BuildMod failed with exit code $LASTEXITCODE." -ForegroundColor Red
    Write-Host "Scroll up to the FIRST error, not the last - the tail is usually teardown noise." -ForegroundColor Yellow
    Write-Host "Re-run with -Verbose to see the exact arguments handed to UAT." -ForegroundColor Yellow
    throw "BuildMod failed."
}

if (-not (Test-Path $output)) {
    throw "BuildMod reported success but no .pak at $output"
}

$size = [math]::Round((Get-Item $output).Length / 1MB, 2)
$mins = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
Write-Host "OK  $output  ($size MB, $mins min)" -ForegroundColor Green
