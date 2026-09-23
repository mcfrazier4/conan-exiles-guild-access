# Phase 1 — find the hook

Goal: answer the open questions in `DESIGN.md` §7 with **real asset and function
names** from the dev kit. No code is written in this phase.

Question 1 — *is the container access check reachable from Blueprint at all?* —
decides whether the project is viable as designed. Everything else waits on it.

Fill in the findings table at the bottom as you go. Screenshots are fine; paste
them to me and I'll work from them.

---

## The two tools that matter

**Find in Blueprints** — `Ctrl+Shift+F`. Searches function names, variable
names, and node names across every Blueprint in the project at once. This is the
single most useful thing in the editor for what we're doing. Most of the tasks
below are a Find in Blueprints query.

**The Override dropdown** — open any Blueprint, and in the **My Blueprint**
panel on the left, hover the **Functions** header. A **+ Override** dropdown
appears. That dropdown lists *exactly* the native C++ functions this Blueprint
is permitted to override.

That dropdown is the answer to Question 1. If a container permission function
appears in it, we can hook it. If it doesn't, we can't, and we redesign.

Secondary: right-click any asset in the Content Browser → **Reference Viewer**
shows what uses it. Good for tracing which blueprint a real in-game chest
actually is.

---

## Asset map

Located by searching the dev kit's content tree on disk, 2026-09-23. All paths
are relative to `Content/` - paste the name into the Content Browser search.

### Open these first

    Systems/Building/BuildingFunctionLibrary          <- task 1.1b
    Items/Weapons/ItemFunctionLibrary                 <- task 1.1b
    Systems/Building/Placeables/BP_PlaceableItemContainer   <- THE container
    Systems/Building/BuildingActorComponents/BP_BAC_Storage <- storage component
    Systems/Building/BP_BuildDoor                     <- THE door
    Systems/Building/BP_BuildingBase                  <- building parts base
    Systems/Building/Placeables/BP_Master_Placeables  <- placeables base

### Also relevant

    Systems/Building/BuildingActorComponents/BP_BAC_CraftingStation  <- task 1.5
    Systems/Building/Placeables/BP_PlaceableArmorDisplayContainer
    Systems/Building/Placeables/BP_PL_DefaultPlaceable
    Systems/Building/BPI_Placeable_PlayerController_Interface
    Characters/FuncomFunctionLibrary

Doors come in tiers and variants (`BP_BuildDoor_T2`, `_T3`, `_Sliding`,
`BP_BuildTrapdoor`), which is exactly why task 1.1 needs the shared parent
rather than a per-door override.

`BuildingActorComponents` holds `BP_BAC_*` components bolted onto placeables -
`BP_BAC_Storage`, `BP_BAC_CraftingStation`, `BP_BAC_UsesFuel` and so on. If
container access is gated anywhere in Blueprint, `BP_BAC_Storage` is the single
most likely place.

### A warning sign

A search across `Systems/` for assets named for *permission*, *access*,
*owner*, *guild*, *clan* or *rank* returned **nothing relevant** - only a purge
navmesh area and two clan-emblem decorations. There is no Blueprint asset that
looks like a permission system.

That is weak evidence that ownership and access checks live in native C++,
which is the failure mode described in Open Question 1. It makes task 1.2 the
decisive test rather than a formality. Do not be discouraged if the check is
not reachable - find out what *is* overridable and bring back the list.

## Tasks

### 1.1 — Map the placeable class hierarchy

Find `BP_Master_Placeables` in the Content Browser. Open it, then
**Class Settings** in the toolbar, and read **Parent Class**.

Then find the blueprint for an ordinary wooden box or chest, and walk its parent
chain upward until you reach `BP_Master_Placeables` or a C++ class. Write down
each step.

Do the same for a basic door.

We need to know the lowest shared ancestor of "things this mod protects",
because that's where the override goes — one override covering everything beats
forty covering each chest type.

### 1.1b — Read Funcom's function libraries FIRST

Spotted 2026-09-23 in the Pick Parent Class dialog: Funcom ship their own
`BlueprintFunctionLibrary` subclasses. A function library is a flat list of
callable functions, so these are far cheaper to read than searching the whole
asset tree:

    BuildingFunctionLibrary        <- doors, placeables, ownership
    ItemFunctionLibrary            <- containers, inventory
    FuncomFunctionLibrary          <- general helpers
    SurvivalFunctionLibrary
    SpellcastFunctionLibrary
    MountFunctionLibrary
    Dialogue2FunctionLibrary
    SoundFunctionLibrary
    RenderToTextureFunctionLibrary

Open `BuildingFunctionLibrary` and `ItemFunctionLibrary` and read the function
list. Ownership, permission, and access helpers are very likely sitting there in
plain sight. Do this before tasks 1.2-1.4.

### 1.2 — Find the access check

Find in Blueprints, and also the Override dropdown on the container blueprint.
Search terms, in rough order of likelihood:

    CanAccess        CanInteract       CanUse          CanOpen
    IsAllowedTo      HasPermission     CheckAccess     CanLoot
    IsOwner          IsOwnedBy         CanBeUsedBy

Record: the exact function name, which class declares it, its signature, and
**whether it appears in the Override dropdown**.

### 1.3 — Find the rank accessor

How do we ask "what rank is this player in their clan?"

Content Browser and Find in Blueprints for: `Guild`, `Clan`, `Rank`. Note that
Conan internally calls clans **guilds** in a lot of places, so search both words
— `Guild` is more likely to hit than `Clan`.

Also try: open any Blueprint graph, right-click on empty canvas, and type
`rank` or `guild` into the node search box. That lists callable functions.

Record: the enum type for rank, its member names, **their numeric order**, and
the function that gets a player's rank.

Do not assume Recruit < Member < Officer < Leader in the enum's actual ordering.
Verify it.

### 1.4 — Find ownership

On `BP_Master_Placeables`, look at the **Components** panel and the **Variables**
list for anything holding an owner: `OwnerId`, `GuildId`, `ClanId`, or an
ownership component.

We need to distinguish clan-owned from personally-owned placeables, because the
mod must leave personal property alone.

### 1.5 — Audit the crafting-station hole

Conan crafting benches can pull materials from nearby containers. Find the bench
blueprint and work out how it enumerates and reads those containers.

**The question that matters:** does that path call the same permission check as
opening the container by hand?

If yes, we get it for free. If no, this is a second override and a real
design problem — a Recruit could drain a locked chest through a bench.

### 1.6 — Find the interaction menu

How are the interaction options on a placeable assembled? Can a mod append an
entry without overriding the menu itself?

Search: `Interact`, `Interaction`, `RadialMenu`, `UseOption`, `ContextMenu`.

### 1.7 — Check `SaveGame` persistence

Lower priority; can slip to Phase 3. On the placeable blueprint, check whether
existing variables use the **SaveGame** flag (visible in a variable's Details
panel). If vanilla variables use it, that's good evidence the serialiser honours
it and option A in `DESIGN.md` §4 is viable.

---

## Findings

| # | Question | Answer | Confidence |
|---|---|---|---|
| 1.1 | Container parent chain | | |
| 1.1 | Door parent chain | | |
| 1.1 | Lowest shared ancestor | | |
| 1.2 | Access check function | | |
| 1.2 | **In Override dropdown?** | | |
| 1.3 | Rank enum + ordering | | |
| 1.3 | Get-player-rank function | | |
| 1.4 | Ownership component/vars | | |
| 1.5 | Bench shares access check? | | |
| 1.6 | Interaction menu appendable? | | |
| 1.7 | SaveGame used by vanilla? | | |

## If 1.2 comes back negative

If no permission function is overridable from Blueprint, the design in
`DESIGN.md` does not work and we pick from:

- **Gate the interaction instead of the access** — override whatever *does* let
  us intercept the interaction before the container opens.
- **Substitute our own container class** — our own placeables derived from the
  vanilla ones, with the check built in. Only protects chests players build
  *from our mod*; existing chests stay unprotected. Weaker, but shippable.
- **A separate lock placeable** that players attach to a container, gating the
  interaction at the lock.

Bring me the finding before picking. The choice depends on exactly what *is*
overridable, and I'd rather reason about the real list than a hypothetical one.
