# GuildAccess — design

Per-object, rank-gated access control for doors and containers in Conan Exiles
Enhanced (UE 5.6.1).

Status: **pre-implementation.** Everything below marked `UNKNOWN` depends on
Phase 1 discovery in the dev kit. Nothing here is verified against the real
asset graph yet.

---

## 1. Rank model

The game's clan ranks are fixed and ordinal. We treat them as integers:

| Rank | Value |
|---|---|
| Recruit | 0 |
| Member | 1 |
| Officer | 2 |
| Leader | 3 |

> `UNKNOWN`: the actual enum name and member names in the dev kit. Conan
> internally calls clans "guilds" in many places, so search both. Confirm the
> ordering is ascending — do not assume.

Every protected placeable stores a single `RequiredRank` integer. Access is
granted when `PlayerRank >= RequiredRank`.

**`RequiredRank` defaults to 0.** This matters: a freshly installed mod must not
change the behaviour of a single existing chest. Players opt in per object.

## 2. Access rules

Granted if **any** of:

- Player is a server admin (bypass).
- Player is the clan **Leader** (always allowed — prevents permanent lockout).
- Object is not clan-owned (personal property; vanilla rules, untouched).
- `PlayerRank >= RequiredRank`.

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

## 3. Enforcement points

All checks are **server-side**. The client UI is a convenience and is never the
gate.

| # | Surface | Status |
|---|---|---|
| 1 | Opening a container's inventory | primary target, `UNKNOWN` hook |
| 2 | Opening / closing a door | primary target, `UNKNOWN` hook |
| 3 | Crafting stations pulling materials from nearby containers | **known hole** — see below |
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

1. Is the container access check reachable from Blueprint at all, or is it
   native C++ with no hook? **This decides whether the project is viable as
   designed.** Phase 1, first task.
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
