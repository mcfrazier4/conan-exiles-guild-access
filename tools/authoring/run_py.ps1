param([string]$Script, [string]$Mode = "dry", [switch]$ModDevKit, [string]$Target = "")
$dk = "C:\Program Files\Epic Games\CEUE5Devkit"
$sp = $PSScriptRoot
$env:GA_MODE = $Mode
if ($Target) { $env:GA_TARGET = $Target }
$log = Join-Path $sp ("{0}{2}.{1}.log" -f [IO.Path]::GetFileNameWithoutExtension($Script), $Mode, $(if ($Target) { "." + $Target } else { "" }))
$args = @("$dk\UE4\ConanSandbox.uproject", "-run=pythonscript", "-script=$sp\$Script", "-stdout", "-FullStdOutLogOutput", "-unattended", "-nopause", "-nosplash", "-NoAssetRegistryCache")
if ($ModDevKit) { $args += "-ModDevKit" }
& "$dk\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" @args *> $log
$out = New-Object System.Collections.Generic.List[string]
$keep = $false
foreach ($l in (Get-Content $log)) {
  if ($l -match '^======== ') { $keep = $true; $out.Add($l); continue }
  if ($l -match '^\[[^\]]+\]\[\s*\d+\](\w+): (Error: |Warning: )?(.*)$') {
    if (($Matches[1] -eq 'LogPython' -and $Matches[3].Trim()) -or ($keep -and $Matches[1] -in @('LogSavePackage','LogBlueprint','LogModDevKit'))) { $out.Add($Matches[3]) }
    continue
  }
  if ($keep -and $l.Trim() -and -not $l.StartsWith('  Either')) { $out.Add($l) }
}
$txt = [IO.Path]::ChangeExtension($log, ".txt")
$out | Set-Content $txt -Encoding utf8
$out
