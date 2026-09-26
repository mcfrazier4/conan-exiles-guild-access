# Steam Workshop listing

Supplied by the project owner 2026-09-23. Thumbnail replaced 2026-09-23 (1408x1408, 748 KB). **Published 2026-09-23: Workshop ID 3807033854** (https://steamcommunity.com/sharedfiles/filedetails/?id=3807033854), visibility Public, uploaded from the dev kit panel as mcfrazieriv. The dev kit copies the preview to `GuildAccess/preview.png` and stores the ID under `steamWorkshopFileIds.mainClient` in modinfo.json.

| Field | Value |
|---|---|
| Name | **Better Guild Control** |
| Description | `description.bbcode` (Steam BBCode, paste verbatim) |
| Preview image | `preview.png` (1024x1024, 256 colours, 869 KB) — dev kit limit is **< 1 MB** |
| Visibility at first upload | Hidden (`steamVisibility: 2` in `modinfo.json`) |

## Before uploading

- `modinfo.json` still says `"name": "GuildAccess"` and has an empty
  `description`. The dev kit's Mod info panel writes those fields to Steam.
  Decide whether the in-game mod list should show "GuildAccess" or
  "Better Guild Control" before changing `name` — it is also the folder name.
- The description's promises (doors, guild-master UI) are built and were
  verified live on 2026-09-23 (docs/PHASE-3-5-PROGRESS.md). Building-part
  doors (`BP_BuildDoor`, hinged doors in doorframes) are NOT covered yet; say so in
  the listing or build them first.
- `bRequiresLoadOnStartup` and `devkitRevisionNumber` in `modinfo.json` must
  be right for the dev kit version at upload time (docs/PHASE-0-SETUP.md 7b).
