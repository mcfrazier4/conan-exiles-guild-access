# Plan: clan rank permissions and an in-game admin panel (v2)

Drafted 2026-09-24 from the owner's brief. Nothing here is built. Items marked
UNKNOWN need a dev-kit probe before they are promised.

## 1. Goal

Turn the four built-in ranks into something a guild master can *configure*:
a name for each rank, and a visible table of what each rank may do. Today the
mod gates one action (open a rank-locked door/container) per object. v2 adds
clan-wide permissions per rank and a panel to manage them.

## 2. What the game gives us (to verify)

| Thing | Vanilla state | Confidence |
|---|---|---|
| Rank count / order | Fixed: Recruit 0, Member 1, Officer 2, Guild Master 3 | confirmed (ERank) |
| Rank names | Fixed strings from the localisation table | confirmed; not editable per clan |
| Rank powers | Officer+: invite, kick lower ranks, promote/demote (UNKNOWN exact matrix); GM: rename clan, MOTD, disband | UNKNOWN - probe the clan UI / `GuildManager` functions |
| Building rights | **Any member can dismantle, repair, upgrade, move and pick up any clan building piece or placeable** | confirmed by play; this is the hole the brief describes |
| Container/door rights | vanilla: any member; **this mod: per-object rank** | done |
| Per-clan storage | none exposed; the ModController can hold SaveGame variables (Funcom's docstring says so) | UNKNOWN until tested |

Research tasks (headless probes, no GUI):

1. List `GuildManager` / `Guild` functions exposed to Blueprint - which rank
   checks exist natively, and what `HasPermission`-style calls, if any.
2. Find where dismantle / pick-up / repair / move are decided
   (`MasterPlaceables_HandleDismantling`, `MasterPlaceables_HandleReturnToInventory`,
   `MasterPlaceables_HandlePlaceableMovement`, and the building-piece
   equivalents on `BP_BuildingBase`). All four are already in Master's
   `InteractableMenu` sequence, so the hook points are known for placeables.
3. Confirm the ModController persists a SaveGame map across restarts.

## 3. Permission model

Per clan, a table `Rank x Permission -> allowed`, stored once (not per object):

```
                     Recruit  Member  Officer  Guild Master
open rank-locked     (per object, unchanged - v1)
dismantle piece        [ ]     [x]     [x]      [x]
pick up placeable      [ ]     [x]     [x]      [x]
move placeable         [ ]     [x]     [x]      [x]
repair                 [x]     [x]     [x]      [x]
upgrade tier           [ ]     [ ]     [x]      [x]
set access rank        [ ]     [ ]     [x]      [x]   (today's rule: rank >= Officer)
edit rank names        [ ]     [ ]     [ ]      [x]
edit this table        [ ]     [ ]     [ ]      [x]
```

Rules that do not need a checkbox because they are structural:

- Guild Master is always all-allowed and cannot be edited (the top row in the
  brief).
- **Only the Guild Master edits.** Every other member can open the panel and
  read it (rank names, who may do what) but every control is disabled for
  them. Decided 2026-09-24.
- **A rank may never dismantle or pick up an object whose access rank is above
  its own.** This closes the "destroy the door to get in" hole regardless of
  how the table is configured. Implemented as: dismantle/pick-up checks
  `MeetsRankRequirement(rank, RequiredRank)` first, then the table.
- Doorframes: the frame has no access rank of its own; the door in it does.
  Dismantling a frame drops its door, so the frame inherits the door's
  requirement while a door is socketed (UNKNOWN: how to find the socketed
  door from the frame - probe `BP_BuildDoorFrame` / `BP_BuildSocket_Door`).

Defaults = vanilla behaviour, so installing v2 changes nothing until a guild
master edits the table (same principle as v1's default rank 0).

Decided 2026-09-24: **repair is a regular permission row** (default allowed for
all ranks), and configuration is **per clan only** - no server-wide default.

## 4. Custom rank names

Four strings per clan, defaults "Recruit / Member / Officer / Guild Master".
Used everywhere the mod prints a rank (submenu labels, hover text, denial
messages, the panel). Vanilla screens (the Clan tab's chevrons) keep showing
vanilla; we cannot rename the game's own rank icons without overriding the
clan widget.

## 5. Storage and replication

- One `FGuildPermissions` struct per clan `{names[4], allowed[4][N]}` in a map
  keyed by guild id on the **ModController** (server, SaveGame). Needs the
  persistence probe in section 2.
- Clients need a copy to draw the panel and to hide menu entries: the
  ModController "is always relevant to all players" and can replicate
  properties, so a replicated map works if the number of clans is modest;
  otherwise send only the local player's clan row through the existing
  `BPC_GA_Player` component (server -> client RPC).
- Edits go client -> server through `BPC_GA_Player` exactly like the rank
  setter (owned component, Run on Server, server re-checks the editor is GM).

## 6. Enforcement points (server-authoritative, as always)

| Action | Where the decision is made | Family |
|---|---|---|
| dismantle / pick up / move | `MasterPlaceables_Handle*` composites feeding the menu, plus the server RPCs they call (UNKNOWN names) | placeables |
| dismantle / repair / upgrade building piece | `BP_BuildingBase` menu + server side (UNKNOWN) | building pieces |
| invite / kick / promote | vanilla clan UI - out of scope for v2 unless the calls are Blueprint-reachable | clan |

Hiding a menu entry is cosmetic; the server RPC behind it must check too, or
a modified client bypasses it.

## 7. The panel

Three ways to open it, best first:

1. **A "Clan Ranks" button on the vanilla Clan tab** (the green box in the
   brief). Requires overriding the clan-tab widget. UNKNOWN which widget; it
   is one of the most-overridden UI assets in the modding scene, so conflicts
   with other mods are likely. Probe first, decide after.
2. **A keybound panel** (mod-owned widget opened by a configurable key via the
   ModController). No override, no conflicts; discoverability is worse - add
   the key to the mod description and a one-time HUD hint.
3. A radial-menu entry on any clan-owned object ("Clan Ranks…"). Cheapest to
   build with the machinery we already have; least elegant.

Layout, from the brief: ranks across the top (Recruit -> Guild Master, left to
right), permissions down the left, checkmarks in the cells, Guild Master
column locked on. Rank names editable inline in the header row (GM only; the
panel is read-only for everyone else). Reuse the roster's row styling so it
reads as part of the Clan screen.

**Rank badges.** The Clan roster already draws a chevron badge per rank (one
chevron for Recruit up to the stacked chevrons for Guild Master). Reuse those
exact textures: as the column headers of the table, and as the icons of the
four circles in the radial "Set Access Rank" submenu (today all four use the
lock icon). Probe: find the badge textures / the widget that maps ERank to
badge (UNKNOWN asset names - do not guess), and check they are plain
`Texture2D`s so `RadialMenuEntry.AddSubItem(icon)` accepts them.

Authoring reality: UMG widgets are the one thing the headless Python route has
not touched. Expect the panel to be built in the GUI (owner) from a written
spec, with the logic behind it (data, RPCs, checks) authored headlessly.

## 8. Order of work

1. Probes: guild API surface, dismantle/pick-up hook points, ModController
   persistence, clan-tab widget name. One day.
2. Storage + replication on the ModController, with a console-only way to
   edit it. Enforce the "cannot dismantle above your rank" rule. Test on the
   local server with the ghost-GM trick.
3. Rank names wired into all existing text; rank badges on the radial
   submenu circles (small, independent of the panel - can ship first).
4. Panel via route 2 (keybound) so it ships without a widget override; route
   1 as a later option if the override is clean.
5. Workshop update with a change note listing the new permissions.
