# Steam Workshop listing

Supplied by the project owner 2026-09-23. Thumbnail replaced 2026-09-23 (1408x1408, 748 KB). Not uploaded yet.

| Field | Value |
|---|---|
| Name | **Guild Access Levels** |
| Description | `description.bbcode` (Steam BBCode, paste verbatim) |
| Preview image | `preview.jpg` — dev kit limit is **< 1 MB** |
| Visibility at first upload | Hidden (`steamVisibility: 2` in `modinfo.json`) |

## Before uploading

- `modinfo.json` still says `"name": "GuildAccess"` and has an empty
  `description`. The dev kit's Mod info panel writes those fields to Steam.
  Decide whether the in-game mod list should show "GuildAccess" or
  "Guild Access Levels" before changing `name` — it is also the folder name.
- The description's promises (doors, guild-master UI) are built and were
  verified live on 2026-09-23 (docs/PHASE-3-5-PROGRESS.md). Building-part
  doors (`BP_BuildDoor`, hinged doors in doorframes) are NOT covered yet; say so in
  the listing or build them first.
- `bRequiresLoadOnStartup` and `devkitRevisionNumber` in `modinfo.json` must
  be right for the dev kit version at upload time (docs/PHASE-0-SETUP.md 7b).
