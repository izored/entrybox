# EntryBox shortcut installer (Windows).
# Creates Start Menu + Desktop shortcuts that launch EntryBox as an app
# window (server auto-starts if it is down). Windows does not allow scripts
# to pin to the taskbar; after this runs, pin it yourself in two clicks:
#   Start menu -> right-click EntryBox -> Pin to taskbar
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$launcher = Join-Path $repo "scripts\windows\entrybox-launcher.vbs"
$icon = Join-Path $repo "assets\entrybox.ico"

if (-not (Test-Path $launcher)) { throw "launcher not found: $launcher" }

$shell = New-Object -ComObject WScript.Shell
$targets = @(
    (Join-Path ([Environment]::GetFolderPath("Programs")) "EntryBox.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "EntryBox.lnk")
)

foreach ($lnkPath in $targets) {
    $lnk = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath = "$env:WINDIR\System32\wscript.exe"
    $lnk.Arguments = "`"$launcher`""
    $lnk.WorkingDirectory = $repo
    if (Test-Path $icon) { $lnk.IconLocation = "$icon,0" }
    $lnk.Description = "EntryBox - the idea board that lives in your repo"
    $lnk.Save()
    Write-Host "created: $lnkPath"
}

Write-Host ""
Write-Host "Done. To put it on the taskbar: open the Start menu, right-click"
Write-Host "EntryBox, and choose 'Pin to taskbar'."
