# Phases 3-5 progress (per-object rank, UI, doors)

All authoring is headless via `UnrealEditor-Cmd.exe -run=pythonscript`; see
docs/AUTOMATION.md. Each step is built in a dry run, applied, then verified by
re-running the idempotent script in dry mode against the saved assets.

## A1 - per-placeable rank (applied 2026-09-23, commit 1718391)

| Asset (override) | Change |
|---|---|
| `BP_Master_Placeables` | `+ RequiredRank` (Byte, RepNotify -> `OnRep_RequiredRank`, default 0). Shared parent of chests **and** placeable doors, so it exists once for "any placeable". |
| `BP_PlaceableItemContainer` | `CanAccessContainer` now reads `RequiredRank` instead of the literal 3. |
| `BP_PL_Door` | `Event Custom Interaction` (the placeable-door open logic) is gated: `GetPawnRank -> IsGuildMemberRank / MeetsRankRequirement(RequiredRank) -> Branch`. Denied = the door does nothing (silent, v1). |

Default 0 means A1 alone changes nothing observable until a rank is set.

## A2 - the setter: lock icon, rank submenu, server-side apply (applied 2026-09-23)

### The client-to-server problem and how it is solved

A Run-on-Server event only works on an actor the client **owns**. Players do
not own placeables, and the vanilla mod-friendly answer is Conan's
`ModController.AdditionalClassComponents`: a mod-owned component that the game
attaches to an existing class without overriding it. So:

```
client                                     server
------                                     ------
hold E on a placeable
  -> Master.InteractableMenu (client)      (nothing)
     "Set Access Rank" + 4 sub-items
click a rank
  -> local PlayerController
     .BPC_GA_Player.ServerSetRequiredRank(Target=placeable, NewRank)   ---RPC--->
                                           BPC_GA_Player (server copy, owned by that client):
                                             Lock = Target.GuildAccessLock
                                             Lock.PendingRank = NewRank
                                             Lock.PendingInstigator = owning controller
                                             Lock.Activate(reset=true)      <- the "request" signal
                                           Master.OnComponentActivated(GuildAccessLock):
                                             HasAuthority
                                             IsOwner(pawn) AND RankCanSetRequired(pawnRank, RequiredRank)
                                             NewRank <= 3
                                             Set RequiredRank (RepNotify)  -> replicates to clients
                                             ConanBuildingPersistence.SetDirty
                                             ClientHUDShowNotification("Access rank set to <rank>")
                                           else ClientHUDShowNotification("You cannot change this access rank", negative)
```

Why the odd `Activate` signal: the Python API can create Blueprint event
dispatchers but cannot place "Call" / "Bind" / "Assign" nodes for them, and it
cannot cast to a Blueprint class created in the same session. The native
`ActorComponent.Activate(bReset) -> OnComponentActivated` delegate is wired
through the official component-bound-event API instead, and the payload rides
in two plain variables on the component. It is a documented convention, not
an accident; see docs/AUTOMATION.md.

### Assets

| Asset | Kind | Purpose |
|---|---|---|
| `Local/BPC_GA_Lock` | ActorComponent | Payload carrier: `PendingRank: Byte`, `PendingInstigator: Controller`. Added to `BP_Master_Placeables` as an SCS component named `GuildAccessLock` (so every placeable has it on both sides). |
| `Local/BPC_GA_Player` | ActorComponent, Replicates | Event `ServerSetRequiredRank_0(Target: Actor, NewRank: Byte)`. **Run on Server + Reliable must be ticked in the GUI** (see below). |
| `Local/BP_GA_ModController` | ModController | `AdditionalClassComponents = [FunCombat_PlayerController_C <- BPC_GA_Player, rule SERVER, tag GuildAccess]`. Discovered automatically by `UModManager::GetActiveModControllerClasses`. |
| `Local/BPL_GuildAccess` | library | `+ RankToText(Rank) -> Text` (pure), `+ RankCanSetRequired(Rank, CurrentRequired) -> Bool` (pure): member AND rank >= current AND rank >= Officer. |
| `Content/.../BP_Master_Placeables` | override | SCS `GuildAccessLock`; server handler; menu appended as a 5th output of the owner-menu Sequence; hover text. |

### Menu rules (client side, cosmetic - the server re-checks everything)

The "Set Access Rank" item (lock icon, subtitle "Current: <rank>") appears only
inside vanilla's `IsOwner` branch and only when `RankCanSetRequired(myRank,
RequiredRank)` holds: clan member, rank >= the current requirement, rank >=
Officer. Sub-items: Recruit / Member / Officer / Guild Master, each with a
one-line description.

### Hover text

`InteractableGetSimpleDisplayText` returns `"<buildable name> - Requires
<rank>"` when `RequiredRank > 0`, otherwise the vanilla empty text. UNKNOWN
until tested: how the HUD renders a non-empty simple display text (it may
replace the name line rather than add to it).

## Two GUI steps the Python API cannot do

Both are single checkboxes in the Details panel. Do them once, then Save.

1. **Run on Server**: open `Content/Mods/GuildAccess/Local/BPC_GA_Player`
   (double-click). In the graph, click the red event node
   `ServerSetRequiredRank_0` once to select it. In the **Details** panel on the
   right, find **Graph > Replicates** and change the dropdown from
   `Not Replicated` to **`Run on Server`**. Tick **Reliable** next to it.
   Compile, Save.
2. **SaveGame**: open `BP_Master_Placeables` (the mod's copy - use the Content
   Browser search inside `Content/Mods/GuildAccess/Content/...`). In **My
   Blueprint** (left), under Variables, click `RequiredRank`. In Details, expand
   the **Variable** section (click the small down-arrow at the bottom of it if
   `SaveGame` is hidden) and tick **SaveGame**. Compile, Save.

Without step 1 the rank click does nothing (the RPC is dropped client-side).
Without step 2 the rank resets on server restart.

## Test plan (after both GUI steps and a deploy)

1. Recreate a clan. Place a chest and a placeable door.
2. Hold E on the chest: the radial menu shows **Set Access Rank** with a lock
   icon and subtitle "Current: Recruit". Open it: four circles + back.
3. Pick **Guild Master**: HUD notification "Access rank set to Guild Master".
   Hover: "<chest name> - Requires Guild Master". Chest still opens (you are GM).
4. Pick **Officer** on the door. Leave the clan and rejoin as ... (solo: not
   possible; see docs/TESTING.md for the DB rank-spoof idea) - or set the rank
   with the admin console instead.
5. Restart the server: the ranks must survive (proves SaveGame + SetDirty).
6. `game_0.db`: `SELECT * FROM properties WHERE name LIKE '%RequiredRank%'`.

## Not yet addressed

- Building-part doors (`BP_BuildDoor`, hinged doors in doorframes) - separate family, next. Trapdoors are out of scope.
- Crafting-bench aggregation (`CanCraftFromNearbyStorages`) - separate path.
- Admin bypass.
- Denial message for doors (chests already get vanilla's "Container is locked!").
- Node positions in the graphs are all (0,0); cosmetic, GUI-only.

## A7 - conflict fix: no more BP_Master_Placeables override (2026-09-24)

Reported live: with LBPR (No_Building_Placement_Restrictions) installed, the
rank options vanished from placeables. LBPR also overrides
`BP_Master_Placeables` (and `BP_BuildingBase`); it loads after us, so its copy
replaced ours and our door/container overrides logged
`Failed to resolve bytecode referenced field ... BP_Master_Placeables_C:RequiredRank`.

Fix: the Master override is gone. Everything it carried now lives on the
three leaf classes, each with its own `RequiredRank` (RepNotify + SaveGame),
`GuildAccessLock` SCS component, server handler, radial submenu, hover text
and denial message:

| Override | Menu hook |
|---|---|
| `BP_PlaceableItemContainer` | new `Event InteractableMenu` -> `Parent: InteractableMenu` (the parent-call node is GUI-only: right-click the event, "Add call to parent function"; `author_a7_leaf.py` wires it) -> ours |
| `BP_PL_Door` | vanilla event kept; a Sequence inserted after it feeds ours |
| `BP_BuildDoor` | unchanged from A5 (already leaf-local) |

Override surface is now four leaf classes (`BP_PlaceableItemContainer`,
`BP_PL_Door`, `BP_BuildDoor` + the library and components), none of which
LBPR touches. Verified on the local server with LBPR mounted **after**
GuildAccess: no resolve/load errors, both ModControllers registered.

Cost: non-container, non-door placeables no longer get the menu - which is
correct, they have nothing to lock. The radial circles also now show the
vanilla rank badges (A6). Not yet on the Workshop.

## A8 - radial badges at 50%, centred (2026-09-25)

The vanilla `T_Rank_*` badges are 16x23 and the radial icon slot is 92x92
(the vanilla `MainRadialMenuIcon*` textures), so the badge was stretched to
fill the circle and looked pixelated. `RadialMenuEntry` exposes no icon size,
so the fix is in the texture: `tools/authoring/icons_src/` holds the exported
badges and `T_GA_Rank_*.png` (92x92, badge scaled to 46 px tall, centred).
`author_a8_icons.py` imports them under `/Game/Mods/GuildAccess` (UI texture
group, no mips) and repoints the four `AddSubItem` icon pins on all three
leaf overrides. The four textures are listed in `CookInfo.ini`.
