# GuildAccess — design

Per-object, rank-gated access control for doors and containers in Conan Exiles
Enhanced (UE 5.6.1).

Status: **pre-implementation.** Everything below marked `UNKNOWN` depends on
Phase 1 discovery in the dev kit. Nothing here is verified against the real
asset graph yet.

---

## 1. Rank model

The enum is **`ERank`**, confirmed 2026-09-23 as the return type of
`GetPlayerRank`. Its members:

    ERank::InvalidRank
    ERank::Recruit
    ERank::Member
    ERank::Officer
    ERank::GuildMaster
    ERank::ERank_MAX

Two corrections to the original design:

- The top rank is **`GuildMaster`**, not "Leader".
- There is an **`InvalidRank`** value, almost certainly what a player with no
  guild returns. Every comparison must handle it explicitly rather than let it
  fall through a `>=` test. A guildless player must never satisfy a rank
  requirement.

### Ordering, confirmed 2026-09-23

A `Switch on ERank` node lists the cases in declaration order:

| Member | Value |
|---|---|
| `Recruit` | 0 |
| `Member` | 1 |
| `Officer` | 2 |
| `GuildMaster` | 3 (displayed "Guild Master") |
| `ERank_MAX` | 4 |

### InvalidRank is a security trap

**`InvalidRank` does not appear in the Switch node at all.** Switch-on-enum
omits hidden values, so `InvalidRank` lies outside 0-4. On a `uint8` enum that
very commonly means **255**.

If it is 255, then for a player with no guild:

    PlayerRank (255) >= RequiredRank (any of 0-3)   ->   TRUE

A naive comparison would grant guildless players access to **every locked
container in the game** - the exact opposite of this mod's purpose.

**Rule: test `Rank == InvalidRank` first and deny. Never let it reach an
ordering comparison.** That is correct regardless of the numeric value, so the
value never needs determining.

`BPL_GuildAccess` must expose a single `MeetsRankRequirement(Rank, Required)`
function implementing exactly this, and no call site may compare ranks
directly.

Every protected placeable stores a single `RequiredRank` integer. Access is
granted when `PlayerRank >= RequiredRank`.

**`RequiredRank` defaults to 0.** This matters: a freshly installed mod must not
change the behaviour of a single existing chest. Players opt in per object.

## 2. Access rules

**Denied outright** if `PlayerRank == ERank::InvalidRank` (no guild). This
test comes first and is not overridable by any rule below. See section 1.

Otherwise granted if **any** of:

- Player is a server admin (bypass).
- Player is the **`GuildMaster`** (always allowed — prevents permanent lockout).
- Object is not clan-owned (personal property; vanilla rules, untouched).
- `PlayerRank >= RequiredRank`, evaluated only after the `InvalidRank` test.

Otherwise denied, with a client-side message explaining the required rank.

The mod only ever **tightens** access. A non-clan-member who could not open a
chest in vanilla still cannot; we never grant access vanilla would refuse.

### Who may change `RequiredRank`

Requires `PlayerRank >= max(CurrentRequiredRank, Officer)`.

That is: you must already be able to open the thing, and you must be at least an
Officer. A Recruit cannot demote a vault down to their own level.

The new value may be anything, including a rank above your own — an Officer
sealing a chest for the Leader only is legitimate. The UI should confirm when
the new value would lock the setter out. The Leader bypass guarantees this is
always recoverable.

## 2b. Getting from the pawn to a rank

`CanAccessContainer` hands us an `Interacting Pawn`. `GetPlayerRank` is a method
on a `Guild` object. The route between them, confirmed 2026-09-23:

    Interacting Pawn
      -> cast to Conan Character
        -> GetGuild              (Target is Conan Character)  -> Guild
        -> GetCharacterUniqueID                               -> Player Id
           -> Guild.GetPlayerRank(Player Id)                  -> ERank

Both `GetGuild` and `GetPlayerRank` are pure. `GetPlayerRank` also has a
`ByStableId` variant if the UniqueID route proves unreliable across sessions.

Null-safety matters at every step and must be handled by denying, not by
falling through:

- The pawn may not be a `Conan Character` (thralls, pets, NPCs). Failed cast
  must deny.
- `GetGuild` returns null for a player with no guild. Must deny.
- `GetPlayerRank` returns `ERank::InvalidRank` for a non-member. Must deny.

See section 1 on why the `InvalidRank` case cannot be left to an ordering
comparison.

## 3. Enforcement points

All checks are **server-side**. The client UI is a convenience and is never the
gate.

| # | Surface | Status |
|---|---|---|
| 1 | Opening a container's inventory | **`CanAccessContainer`** on `BP_Master_Placeables` — overridable, confirmed |
| 2 | Opening / closing a door | primary target, `UNKNOWN` hook |
| 3 | Crafting stations pulling materials from nearby containers | **confirmed separate path**: `CanCraftFromNearbyStorages`, `IsAggregatableWith`, `RegisterAggregatableInventories` |
| 4 | "Loot all" / quick-transfer paths | needs audit |
| 5 | Followers (thralls/pets) accessing containers | out of scope for v1 |

### The crafting-station hole

Conan lets crafting benches draw materials from nearby containers. If we only
gate the *open* action, a Recruit can still drain a locked chest by standing at
a bench. Any honest version of this mod has to address surface 3, or document
loudly that it does not. Audit this during Phase 1 — it may share a permission
path with surface 1, in which case we get it for free.

Building damage and raiding are deliberately untouched. This is access control,
not raid protection.

## 4. Persistence

Where `RequiredRank` lives across a server restart. To be settled in Phase 3 by
testing, in this order of preference:

- **A. `SaveGame`-flagged variable on the placeable.** Cleanest if the game's
  serialiser picks up modded properties. Test first.

  Strong precedent found 2026-09-23: `BP_PlaceableItemContainer` already carries
  `InventorySharingAccess` (`EInventoryShare`, values On/Off) as a per-container
  enum that is replicated (`OnRep_InventorySharingAccess`), authority-gated
  (`Switch Has Authority`), broadcast (`OnSharingAccessChanged`) and persisted
  via the `ConanBuildingPersistence` component on the same actor. Our
  `RequiredRank` wants exactly this shape. Copy it rather than invent one.

  Note `EInventoryShare` is only On/Off, so it cannot itself express four rank
  tiers - it is a model, not a vehicle.
- **B. Mod-owned registry actor**, mapping placeable unique ID → rank. See the
  dev kit's "Unique ID migration" docs page before relying on placeable IDs
  being stable.
- **C. Encode into the placeable's custom name field.** Persists reliably
  because it is a vanilla saved property. Ugly, player-visible, and collides
  with people naming their chests. Fallback only.

### Replication constraint

`BP_Master_Placeables` has `IsRepObjectSupported`, defaulting to `true`, which
enables push-model replication. `RequiredRank` is a single replicated int
changed via a server RPC from the owning client, which should be compatible.

Inflexion document a UE 5.6 bug affecting **replicated arrays modified from
non-owning actors**. Do not put an array on the placeable. If the design ever
drifts toward per-player exception lists stored on the object, revisit this.

## 5. Mod conflict strategy

Overriding a base asset means this mod *owns* it. Other mods touching the same
asset conflict, load order decides the winner, and Funcom patches can break us.
This is a public Workshop mod, so it must be a deliberate, minimal, documented
surface.

Rules:

- Override the **smallest possible** function on the **highest-value shared
  parent**, and have it immediately call into `BPL_GuildAccess`, our own mod-
  owned function library. All real logic lives in assets nobody else touches.
- Keep a running list of every overridden base asset in this file, and publish
  it in the Workshop description so other modders can check compatibility.

### Overridden base assets

_(none yet — populate during Phase 2)_

## 6. UI

v1: an entry in the placeable's interaction menu ("Set Access Rank") visible
only to players who pass the change-permission check in §2, opening a small
widget with the four ranks.

> `UNKNOWN`: how interaction menu options are assembled for a placeable, and
> whether a mod can append one without overriding the menu itself.

The denial message on a failed access attempt should name the required rank, not
just refuse.

## 7. Open questions

1. ~~Is the container access check reachable from Blueprint at all?~~
   **ANSWERED 2026-09-23: yes.** `CanAccessContainer` and
   `CanAccessPlaceableInventory` are both overridable from Blueprint, declared
   on `BP_Master_Placeables`. `CanAccessContainer` is pure, with signature
   `(Target: PlaceableBase, InteractingPawn: Pawn)` returning `CanAccess`,
   `ContainerIsLocked` and `InstigatorIsOwner`. The design stands.
2. Does the door check share a code path with the container check, or are they
   separate overrides?
3. Do modded `SaveGame` variables on a base placeable actually persist?
4. Does the crafting-station pull path share the container permission check?
5. Are placeable unique IDs stable across restarts and across the Enhanced
   unique-ID migration?
6. Can interaction menu entries be appended without an override?
7. Does `bRequiresLoadOnStartup` in `modinfo.json` need to be `true` for a mod
   that overrides base-game blueprints? Currently `false` (the dev kit default).
   Prime suspect if the mod loads but its overrides never take effect.
