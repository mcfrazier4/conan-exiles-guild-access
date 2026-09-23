# Phases 3-5 progress (per-object rank, UI, doors)

All authoring is headless via `UnrealEditor-Cmd.exe -run=pythonscript`; see
docs/AUTOMATION.md. Each step is built in a dry run, applied, then verified by
re-running the idempotent script in dry mode against the saved assets.

## A1 - applied 2026-09-23 (commit below)

| Asset (override) | Change |
|---|---|
| `BP_Master_Placeables` | `+ RequiredRank` (Byte, RepNotify -> `OnRep_RequiredRank`, default 0). Shared parent of chests **and** placeable doors, so it exists once for "any placeable". |
| `BP_PlaceableItemContainer` | `CanAccessContainer` now reads `RequiredRank` instead of the literal 3. |
| `BP_PL_Door` | `Event Custom Interaction` (the placeable-door open logic) is gated: `GetPawnRank -> IsGuildMemberRank / MeetsRankRequirement(RequiredRank) -> Branch`. Denied = the door does nothing (silent, v1). |

Default 0 means **this build changes nothing observable** until a rank is set.
That is the point of the first live test: every placeable must still work.

Base-asset override count is now **four**: `BPL_GuildAccess` (ours),
`BP_PlaceableItemContainer`, `BP_Master_Placeables`, `BP_PL_Door`.
`BP_Master_Placeables` is the largest conflict surface in the game; it is
justified because it is the only class both target types share.

Found during A1: Master already implements `Event InteractableMenu`,
`Event InteractableActivate` and `Event InteractableOnCancel` in its
EventGraph. A2 appends to those chains rather than overriding them.

## A2 - next

On `BP_Master_Placeables`:

1. **Owner assignment**: at the end of `Event InteractableActivate`, if the
   interacting player may change the rank, `SetOwner(InstigatorController)` so
   that client may call a Run-on-Server event on this actor (UE delivers
   server RPCs only from actors the client owns).
2. **Setter**: custom event `ServerSetRequiredRank(NewRank: Byte)`, Run on
   Server + Reliable, authority-checked, permission-checked
   (`rank >= max(current, Officer)`), clamps to 0-3, sets `RequiredRank`,
   `ConanBuildingPersistence.SetDirty`, confirms via
   `ClientHudShowNotification`.
3. **Menu**: append to `Event InteractableMenu` - if the local player may
   change the rank, `AddItem("Set Access Rank", subtitle with current rank,
   MainRadialMenuIconLocked)` then four `AddSubItem` entries (Recruit, Member,
   Officer, Guild Master), each bound to a custom event that calls the setter.
4. **Hover**: override `InteractableGetSimpleDisplayText` to show
   "Requires: <rank>" when `RequiredRank > 0`.

## Reserved for the GUI (the Python API cannot do these)

- Tick **SaveGame** on `RequiredRank` in `BP_Master_Placeables` (persistence).
- Set **Replicates = Run on Server, Reliable** on `ServerSetRequiredRank`.

Both are single checkboxes; do them once A2 has created the variable/event.

## Not yet addressed

- Building-part doors (`BP_BuildDoor`, `BP_BuildTrapdoor`) - separate family.
- Crafting-bench aggregation (`CanCraftFromNearbyStorages`) - separate path.
- Admin bypass.
- Denial message for doors (chests already get vanilla's "Container is locked!").
