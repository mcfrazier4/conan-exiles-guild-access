# Phase 0 — get the pipeline working

Goal: an empty `GuildAccess.pak` that builds from the command line and shows up
in the game's mod list. No features. Just proof that every link in the chain
works, before we have any logic worth debugging.

Do not skip to Phase 1. A broken build pipeline discovered later looks exactly
like broken mod logic, and you will waste a day telling them apart.

---

## 1. Dev kit — DONE

Installed and verified 2026-09-23 at:

    C:\Program Files\Epic Games\CEUE5Devkit

Confirmed present: `RunDevKit.bat`, `Engine\Build\BatchFiles\RunUAT.bat`,
`UE4\ConanSandbox.uproject`, and the full `UE4\Content\` game asset tree.

The project sits under `UE4\` even though this is the UE5 kit. That folder name
is a leftover and is correct — the build commands expect it.

### If cooking later fails on paths

This path is 38 characters and contains a space, where the community guidance
is to keep the dev kit somewhere short like `C:\ConanDevKit`. It may well be
fine. Do **not** redownload 160 GB on speculation — wait and see whether
cooking actually fails.

If it does fail with anything path-shaped, make a short alias instead of
reinstalling. In **cmd as Administrator**:

    mklink /J C:\ConanDevKit "C:\Program Files\Epic Games\CEUE5Devkit"

Then build with `tools\build-mod.ps1 -DevKit C:\ConanDevKit`. Costs no disk
space and takes a second.

## 2. Disk space — fine

629 GB free on C:. No need to relocate the Zen Server DDC.

## 3. Launching — `RunDevKit.bat` must run from its own folder

`RunDevKit.bat` contains a bug. It uses `%~dp0` (the script's own folder) for
the project path, but a bare **relative** path for the executable:

    start Engine\Binaries\Win64\UnrealEditor.exe "%~dp0\UE4\ConanSandbox.uproject" -ModDevKit

So it only works if the current directory is already the dev kit root. Run it
from anywhere else and it looks for the editor under *that* folder, finds
nothing, and the trailing `exit` closes the window before you see an error.
It fails completely silently.

Launch it like this instead, from any directory:

    Start-Process -FilePath "C:\Program Files\Epic Games\CEUE5Devkit\RunDevKit.bat" -WorkingDirectory "C:\Program Files\Epic Games\CEUE5Devkit"

To check whether it actually started:

    Get-Process UnrealEditor

The `-ModDevKit` flag the batch file passes is the part that matters — without
it **the mod menu does not appear at all**. Launching from the Epic Games
Launcher's Play button may skip it. If you ever open the editor and there's no
mod menu, that is why.

First launch takes a long time and may look frozen while it compiles shaders
and builds the DDC. Let it run.

## 4. Create the mod

In the dev kit, create a mod named exactly **`GuildAccess`**. This produces:

    C:\Program Files\Epic Games\CEUE5Devkit\UE4\Content\Mods\GuildAccess\

That `Mods` folder does not exist yet — it gets created with your first mod.

All of our assets must live under that folder. Assets placed outside it will
fail to cook.

## 5. Point the dev kit at the repo

So that git tracks the real assets rather than a copy, replace that folder with
a directory junction back to this repo. In **cmd**, after closing the dev kit:

    move "C:\Program Files\Epic Games\CEUE5Devkit\UE4\Content\Mods\GuildAccess" "E:\ClaudeCode\conan-exiles\guild-access\GuildAccess"
    mklink /J "C:\Program Files\Epic Games\CEUE5Devkit\UE4\Content\Mods\GuildAccess" "E:\ClaudeCode\conan-exiles\guild-access\GuildAccess"

`/J` creates a junction and works across drives.

If the dev kit behaves strangely with the junction — cook failures that mention
paths, or assets that vanish from the Content Browser — tell me and we'll swap
to a sync script instead. Junction first because it has no drift.

## 6. Build headlessly

    tools\build-mod.ps1

Output lands at:

    C:\Program Files\Epic Games\CEUE5Devkit\UE4\Saved\Mods\GuildAccess\Output\GuildAccess.pak

We build from the command line rather than the editor's package button because
I can run and debug this with you, and the editor GUI I cannot.

## 7. Install and verify in-game

1. Copy the `.pak` somewhere stable, e.g. `C:\ConanMods\GuildAccess.pak`.
2. Add the full path as a line in
   `C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles\ConanSandbox\Mods\modlist.txt`.

   Every line in that file is currently commented out with `#`, so you are
   running vanilla. Keep it that way — a clean baseline is what we want for
   testing. Add only ours, uncommented.
3. Launch the game. The mod should appear in the mod list.

**That is the Phase 0 finish line.** An empty mod that loads.

## 8. Set up a test server

Real testing needs a **dedicated server** plus two accounts at different clan
ranks. Play-In-Editor will not reproduce genuine clan membership and rank state,
which is precisely the thing this mod reads.

Budget time for this. Testing a permission system with one account tells you
almost nothing.

## Checklist

- [x] Dev kit installed (169 GB, `C:\Program Files\Epic Games\CEUE5Devkit`)
- [x] Disk space confirmed
- [x] Launches via `RunDevKit.bat` (with `-WorkingDirectory`, see section 3)
- [x] `GuildAccess` mod created
- [x] Junction from dev kit to repo in place (`tools\link-mod.ps1`, verified 2026-09-23)
- [ ] Headless build produces a `.pak`
- [ ] `.pak` appears in the in-game mod list
- [ ] Dedicated server running, two accounts, one clan, different ranks
