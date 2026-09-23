# Testing strategy

## The constraint

Testing is **solo**. There is no second account that owns Conan Exiles, so no
second character can be put in a clan at a lower rank.

That means exactly two `ERank` values are reachable in a live test:

| State | Rank observed |
|---|---|
| Not in a clan | `ERank::InvalidRank` |
| In your own clan | `ERank::GuildMaster` (3) |

`Recruit` (0), `Member` (1) and `Officer` (2) cannot be produced, because a
clan of one has only a GuildMaster and you cannot demote yourself.

## What this does and does not cover

**Covered, and these are the parts that matter most:**

- The override actually fires, and on the server.
- The pawn -> Conan Character -> Guild -> `GetPlayerRank` chain returns a real
  rank rather than failing silently.
- **The `InvalidRank` guard.** Leaving your clan reproduces the exact case that
  would otherwise grant guildless players access to everything. This is the
  highest-severity bug in the design and it is fully solo-testable.
- Denial actually blocks, rather than merely changing what the UI reports -
  see "Forcing a denial" below.
- The failed-cast path, by having a thrall or pet interact with a container.

**Not covered:**

- Ordering comparisons between `Recruit`, `Member` and `Officer`. These reduce
  to an integer `>=` on an enum whose ordering is already confirmed
  (Recruit 0 < Member 1 < Officer 2 < GuildMaster 3), so the residual risk is
  low - but it is not zero and should be stated plainly in the Workshop
  description until someone verifies it with a real clan.

## Forcing a denial without a second account

The trick is to move the *threshold*, not the rank.

1. Make the required rank a variable that can be set without a rebuild - a
   server INI setting, an admin console command, or worst case a constant that
   is cheap to recook.
2. Set it **above** your own rank. Requiring rank 4 (`ERank_MAX`) while you are
   a GuildMaster (3) must deny you.
3. Confirm denial is real: the container must not open, not merely grey out.
   Check the **server** log, not the client's.
4. Then set it to 0 and confirm you are allowed again.

Combined with the clan-leave test for `InvalidRank`, this exercises both sides
of the decision without ever needing a Recruit.

## Log everything during Phase 2

The vertical slice should log, server-side, on every access check:

    pawn class, cast success, guild found, ERank value, required rank, decision

Without a second account, the log is the primary evidence that the logic is
right. Strip the logging before release.

## Servers

### Local dedicated server - use this for development

Free, via Steam. Use the **"Games and Software" dropdown** at the top-left of
the library sidebar to enable **Tools**, then install **"Conan Exiles Dedicated
Server"** (App ID **443030**). Same machine, no upload step, restarts in
seconds.

Installed 2026-09-23 to
`C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles Dedicated Server`
(3.55 GB). The executable is `ConanSandboxServer.exe`.

**Branch matters.** App 443030 serves both `public` (Enhanced / UE5) and
`conan-exiles-legacy` (UE4). The game here is Enhanced 2.2.0, so the server must
be on `public`. That is the default; check Properties -> Betas if the server
refuses connections or rejects the mod.

If it does not appear under Tools, install via SteamCMD: `app_update 443030`.

The Phase 2 loop is rebuild (48s) -> restart -> test, run dozens of times. Keep
it local.

### First run

`ConanSandbox/Mods` and the config files do not exist until the server has run
once. Launch it, let it generate them, then stop it.

Windows will prompt for firewall access on first launch. For local-only testing,
private networks are enough - there is no reason to expose it publicly.

Connect from the game client with **Direct Connect** to `127.0.0.1`.

### Stopping the server

The headless server does not respond to a window-close message, so `taskkill`
without `/F` times out. **Force-killing it is safe.** Conan stores its world in
SQLite with a write-ahead log (`game_0.db` plus `game_0.db-wal`), which is
designed to survive the process dying; the WAL is replayed on next open.

Verified 2026-09-23: after a forced kill, the database still held 90 buildings,
6 building instances, 109 actor positions and 1 character.

    Get-Process ConanSandboxServer* | Stop-Process -Force

Do not wait for graceful shutdowns during the iteration loop. They do not come.

### The iteration loop

    tools\deploy.ps1

Builds the mod and installs it to **both** the client and the server, then
clears `Saved/ExtractedMods` on each.

That last step matters. Both the game and the server extract the mod's
per-platform paks into `Saved/ExtractedMods/` and reuse them. A stale extract
means you are testing old code while believing you are testing new code, with no
error to tell you. Never skip it.

Use `-SkipBuild` to reinstall an existing `.pak` without recooking.

Close the dev kit editor and stop the server before running it: the editor
conflicts with cooking, and the server holds locks on the extracted files.

**Only one build at a time.** AutomationTool takes a global mutex; a second
concurrent run dies instantly with "A conflicting instance of AutomationTool is
already running" and no log file. If that appears, check for leftover `dotnet`
or `UnrealPak` processes before assuming anything is broken - a build already in
flight is the usual cause, and killing it would waste the work.

### G-Portal - use this for pre-release validation only

Available, but each iteration costs an FTP upload and a remote restart. Reserve
it for confirming behaviour under realistic conditions before release.

To get an unpublished mod onto it, either:

- **FTP the `.pak`** into `ConanSandbox/Mods/` and add its path to the server's
  `modlist.txt`, or
- publish a **hidden** Workshop item (`modinfo.json` already has
  `steamVisibility: 2`) and point G-Portal at the ID.

FTP is preferable pre-release: nothing to clean up afterwards.

### Clients need the mod too

Conan mods are client+server. Any account connecting to a modded server needs
the same `.pak` installed locally, listed in its own `modlist.txt`.
