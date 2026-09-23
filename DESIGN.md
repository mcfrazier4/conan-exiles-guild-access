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

**`InvalidRank` = 255, confirmed 2026-09-23.** Extracted from the enum
registration table in `UnrealEditor-ConanSandbox.dll` by parsing the PE,
resolving the `ERank::<Name>` string VAs and reading the paired int64 values:

    Recruit     = 0
    Member      = 1
    Officer     = 2
    GuildMaster = 3
    ERank_MAX   = 4
    InvalidRank = 255

This is measured, not inferred. It confirms the bounds check was the right
design: `InvalidRank` really does sit above every real rank, so a bare `>=`
would have granted guildless players access to everything.

If it is 255, then for a player with no guild:

    PlayerRank (255) >= RequiredRank (any of 0-3)   ->   TRUE

A naive comparison would grant guildless players access to **every locked
container in the game** - the exact opposite of this mod's purpose.

**Rule: a rank outside 0-3 is never granted access.** That is correct
regardless of `InvalidRank`'s numeric value, so the value never needs
determining.

`InvalidRank` cannot be named directly - confirmed 2026-09-23 that it is hidden
from enum literal dropdowns as well as from `Switch on ERank`. So the guard is
written as a **bounds check** rather than an equality test:

    Result = (Rank <= GuildMaster) AND (Rank >= Required)

`Rank <= GuildMaster` excludes `InvalidRank` because being hidden from the
switch means it lies outside 0-4. The lower bound needs no separate test:
`Rank >= Required` covers it, since `Recruit` is 0 and the enum is byte-backed
and unsigned.

`BPL_GuildAccess` must expose a single `MeetsRankRequirement(Rank, Required)`
function implementing exactly this, and no call site may compare ranks
directly.

Every protected placeable stores a single `RequiredRank` integer. Access is
granted when `PlayerRank >= RequiredRank`.

### Default-open is a product decision, not an oversight

**`RequiredRank` defaults to 0 (`Recruit`).** Every guild member satisfies
`PlayerRank >= 0`, so installing this mod changes the behaviour of **zero**
existing objects. Nothing locks until a player deliberately raises it.

This applies to **every placeable and every door**, not just chests.

Stated explicitly by the project owner 2026-09-23: anyone in the guild can open
any chest, door or placeable by default, *unless* someone has set it higher.
The inverse - locking everything and making players open things up - was
rejected as a headache, and it is: a guild of thirty with a thousand placeables
would face an unbounded amount of clicking before the base functioned again.

**Do not reverse this on "secure by default" grounds.** The security boundary
this mod cares about is *within* an already-trusted guild. Vanilla's ownership
rules still run first, via the parent call, so non-members are refused exactly
as before. Default-open here means "as permissive as vanilla", not "open to the
world".

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

**Verified 2026-09-23** by an authority probe: with the override denying only
when `HasAuthority`, the client displayed "Open" in green while the server
refused with "Container is locked!" and the container did not open. The two
disagreed and the server won, so `CanAccessContainer` is genuinely a
server-authoritative decision point.

| # | Surface | Status |
|---|---|---|
| 1 | Opening a container's inventory | **`CanAccessContainer`** on `BP_Master_Placeables` — overridable, confirmed |
| 2 | Opening / closing a door | **`InteractableActivate`** (Interactable Interface) - overridable. Three override points, see section 3b. |
| 3 | Crafting stations pulling materials from nearby containers | **confirmed separate path**: `CanCraftFromNearbyStorages`, `IsAggregatableWith`, `RegisterAggregatableInventories` |
| 4 | "Loot all" / quick-transfer paths | needs audit |
| 5 | Followers (thralls/pets) accessing containers | out of scope for v1. Note vanilla already has a per-door "Lock Door for Thralls" toggle for Living Settlements pathing, which is unrelated to player access but may confuse users if our wording is careless. |

### 3b. Doors are three unrelated families

Confirmed 2026-09-23 by reading parent classes out of the uassets:

    BP_BuildingBase_C
      +- BP_BuildDoor_C          -> BP_BuildDoor_T2, _T3
      +- BP_BuildTrapdoor_C      -> BP_BuildTrapdoor_T2, _T3

    BP_Master_Placeables_C
      +- BP_PL_Door_C
           +- BP_BuildDoor_Sliding_C  -> BP_BuildDoor_Sliding_T3

**Sliding doors are placeables, not building parts.** They share a root with
containers rather than with other doors.

So gating "doors" needs **three** override points, not one:

| Override on | Covers |
|---|---|
| `BP_BuildDoor` | hinged doors, all tiers |
| `BP_BuildTrapdoor` | trapdoors, all tiers |
| `BP_PL_Door` | sliding doors, all tiers |

Tiers inherit, so variants come free. Combined with the container override that
is **four base assets** total - the conflict surface that section 5 is about.

### The door gate

`BP_BuildDoor`'s EventGraph shows the vanilla check in plain Blueprint:

    Event InteractableActivate (from Interactable Interface)
      -> Get Controlled Pawn
      -> IsOwner (Target is Buildable Base, Pawn, SendGuiNotification)
      -> Branch -> Branch (IsOpen) -> OpenDoor timeline -> Set Actor Rotation

Vanilla doors gate on **ownership only**; there is no rank concept. That is the
gap this mod fills.

`IsOwner` is **not** overridable - searching the Override dropdown for "owner"
returns nothing. So we gate at `InteractableActivate` instead, which is
overridable and runs *before* the ownership branch.

Note `IsOwner`'s `SendGuiNotification` pin: the game already has a
check-and-notify pattern. Prefer driving that over inventing our own messaging.

### Interaction surface available to us

All overridable, all declared on `Interactable Interface`:

    InteractableActivate              <- the gate
    InteractableMenu                  <- section 6: adding "Set Access Rank"
    InteractableGetSimpleDisplayText  <- hover text could show required rank
    InteractableCanBeLooted
    InteractableActivateDisabled / InteractableMenuDisabled
    ClientInteractableActivate / Hovered / Unhovered
    GetInteractableBonusRange / InteractableDefaultAction / InteractableShouldCommand

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

### The user journey

The target experience, as specified by the project owner:

| # | Step | Hook | Status |
|---|---|---|---|
| 1 | Build hammer, place door frame, place door | none - vanilla | n/a |
| 2 | Hold E on the door, radial menu shows a permission option | `InteractableMenu` | hook confirmed overridable |
| 3 | Select it, choose a rank (e.g. GuildMaster) | our own widget or a radial submenu | **UNKNOWN** which |
| 4 | Confirmation appears, auto-dismisses | notification system | **UNKNOWN**, but `IsOwner` has a `SendGuiNotification` pin, so a pattern exists |
| 5 | Hovering the door shows its name **and** permission level | `InteractableGetSimpleDisplayText` | hook confirmed overridable |
| 6 | Players below the rank see the requirement and a lock icon, and cannot open it | `InteractableActivate` (doors) / `CanAccessContainer` (containers) | hooks confirmed overridable |

This applies to **both** doors and storage containers. `BP_BAC_Storage`
implements `InteractableInterface`, so steps 2, 4, 5 and 6 share one
implementation across both. Only step 6's enforcement differs: containers gate
at `CanAccessContainer`, doors at `InteractableActivate` (see section 3b).

### What each step still needs

**Step 2 - who sees the option.** Per section 2, only players whose rank is at
least `max(CurrentRequiredRank, Officer)`. Everyone else must not see the entry
at all, rather than see it greyed out. A greyed entry advertises that the
container is rank-locked and roughly by whom.

**Step 3 - a lock icon opening a radial submenu.** Specified by the project
owner 2026-09-23:

- The entry on the door/container wheel uses a **lock icon**.
- Activating it opens a **submenu**, not a cycle and not a separate window.
- Each rank appears as its own **circle** in that submenu.
- The submenu includes a **back / cancel** button.

Every asset this needs already exists in the dev kit:

| Need | Asset |
|---|---|
| Lock icon | `UI/Textures/GUIs/MainRadialMenu/MainRadialMenuIconLocked` |
| Unlocked state | `.../MainRadialMenuIconUnlocked` |
| Back / cancel | `.../T_MainRadialMenuIconCancel` |
| Option-as-circle | `UI/Framework/W_RadialMenuSegment` |
| The wheel | `UI/Framework/W_RadialMenu` |

Using Funcom's own icons and segment widget keeps the mod visually native,
which matters for a public release.

> `UNKNOWN`: whether `W_RadialMenu` supports **nested** submenus, and if so how
> a mod pushes a new page onto it. `UI/Framework/W_SorceryRadial` is a second
> radial implementation and the first place to look for a working nesting
> precedent. If nesting is not supported, the fallback is a UMG widget styled to
> match - not a cycling toggle, which the owner has ruled out.

**Naming caution.** The vanilla door wheel already has "Lock Door for Thralls",
which governs NPC pathing for Living Settlements and has nothing to do with
player access. Our entry must not read as a second thrall lock. Prefer
"Set Access Rank" over anything containing "Lock", even though the icon is a
padlock.

**Step 4 - confirmation timing.** Fire only after the **server** accepts the
change, never optimistically on the client. A confirmation for a change the
server rejected is worse than no confirmation at all.

**Step 5 - hover text carries the feature.** It is the only always-visible
surface, so it is the whole feature's discoverability. It is unknown whether
`InteractableGetSimpleDisplayText` supports multiple lines or icons. Verify
before designing around it.

**Step 6 - the lock icon.** `CanAccessContainer` already returns
`ContainerIsLocked` and vanilla has a container lock concept, so an existing
lock visual may be reusable. Check before drawing our own.

### Non-negotiables

- The denial must **name the required rank**. "You cannot access this" teaches
  the player nothing; "Requires Officer" tells them who to ask.
- Steps 5 and 6 are client-side presentation and must never be the gate. A
  client running modified UI must still be refused by the server.

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
7. **Do client and server mount the mod at different paths, and does that break
   base-asset overrides?** Observed 2026-09-23 with a mod containing only new
   assets:

       client:  mount point '../../../ConanSandbox/Content/'
       server:  mount point '../../../ConanSandbox/Content/Mods/GuildAccess/'

   If that difference persists once the mod contains an override, a base asset
   shadowed on the client might not be shadowed on the server - which for a
   server-authoritative permission check would be fatal. Check this the moment
   the first override exists. It may equally be an artifact of there being no
   overrides yet.

8. Does `bRequiresLoadOnStartup` in `modinfo.json` need to be `true` for a mod
   that overrides base-game blueprints? Currently `false` (the dev kit default).
   Prime suspect if the mod loads but its overrides never take effect.
