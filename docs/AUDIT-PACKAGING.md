# Packaging audit — 2026-09-25

Triggered by players reporting "Guild Access Levels: wrong version" on the mod
mismatch screen while every other mod showed "ok".

## Method

Parsed the outer `.pak` container (UE pak v12) of every Enhanced-format mod in
the local Workshop folder (19 mods, including all 11 running on the G-Portal
server) and of our Workshop build (item 3807033854, manifest 653835836340570914).
Compared `modinfo.json` fields, container layout, and the per-platform inner
paks. Cross-checked against the devkit's own build script
`UE4/Build/ModDevKit.Automation/BuildMod.cs`, which documents the expected
layout and manifest format.

## Result: no deviation

| Property | Other Enhanced mods | Ours |
|---|---|---|
| `steamWorkshopFileIds.mainClient` | equals Workshop folder ID | equals |
| `steamPublishedFileId` | empty on new Enhanced mods; filled only on legacy ports | empty |
| `steamVisibility` | 0 | 0 |
| `folderName` | equals pak basename | equals |
| `devkitRevisionNumber` / `minimumVersion` | 1002 / "Enhanced" | same |
| Container | pak v12, mount `../../../ConanSandbox/Mods/`, 11 uncompressed entries | same |
| Manifest | MD5 map + nested `<xxh128>` map | same |
| Inner paks | `AssetRegistry.bin` + `ModCompat.bin`, identical across Windows / WindowsServer / LinuxServer | same |

Entry order inside the container varies between mods (manifest first on 13,
a binary first on 6, including mods that run fine on the server). Not
significant.

## Root cause of the "wrong version" reports

Not packaging. Timeline (local time):

- Sep 23 18:58 — build A uploaded to Workshop.
- Sep 24 17:56 — build B uploaded to Workshop. Server not updated.
- Sep 24 18:13 — owner joined the G-Portal server with build A (Steam had not
  yet fetched B). Welcomed. Server reported mod hash `2557…`.
- Sep 25 13:52 — a player with build B joined. Server still reported `2557…`.
  Rejected with `ModMismatch`, screen shows "wrong version".

The game's mismatch statuses (from the shipping binary) are `not installed`,
`needs update`, `downloadable`, `updating`, `wrong version`. "wrong version"
means the client has the current Workshop build and the server reports a
different one. It is never a download failure.

Any server that installed the mod between the two uploads and does not re-pull
Workshop content on restart is stale in the same way.

The exact identity-hash formula is `UNKNOWN`. It is not MD5, xxh128, or
truncated SHA of the container, the index, any inner file, the manifest, or
`modinfo.json`, alone or concatenated per platform. It does not need to be
known: the same build matched on both sides for build A, and does for every
other mod, so it is platform-independent and build-specific.

## Rules adopted

1. Bump `versionBuild` in `modinfo.json` on every Workshop upload. Both A and B
   shipped as 1.0.0, so the mismatch screen showed identical versions on both
   sides and admins could not tell they were behind.
2. Update the Workshop and the G-Portal server in the same sitting. Any gap
   locks every player out until the server catches up.
3. Verify by joining the G-Portal server with the Workshop copy. The local
   `modlist.txt` points at `C:\ConanMods\GuildAccess.pak`; a single-player
   session with that pak does not exercise the server handshake.
4. To identify a stale server from any player's `ConanSandbox.log`, read the
   line `Server mod: Guild Access Levels (<hash>)`. Hash `2557…` is build A.
