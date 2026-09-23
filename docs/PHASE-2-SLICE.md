# Phase 2 - the vertical slice

Goal: a container that refuses to open for a player below a required rank,
enforced on the server.

No UI. No persistence. No doors. One hardcoded rank, one override, and proof
that it actually blocks.

The point of the slice is not the feature. It is to answer whether the
architecture in DESIGN.md survives contact with a running server, while the mod
is still small enough to throw away.

---

## Answer these three before writing anything

Each is a ten-minute check, and each can change the approach.

### 2.0a - Can the override call impure nodes?

`CanAccessContainer` is **pure** (green header, no exec pins). Pure Blueprint
graphs cannot call impure nodes, and `Print String` and `Print Text` are
impure.

Create the override and try to place a `Print String` in it.

- **Works** -> the logging strategy in TESTING.md stands.
- **Refused** -> we cannot log from inside the decision, which is a real problem
  because without a second account the log is our primary evidence. Fall back to
  logging from `InteractableActivate`, which is impure, and keep the pure
  function for the decision only.

### 2.0b - Does the override actually apply on the server?

Open question 7 in DESIGN.md. Client and server reported different mount points
for a mod with no overrides:

    client:  ../../../ConanSandbox/Content/
    server:  ../../../ConanSandbox/Content/Mods/GuildAccess/

If a base-asset override is shadowed on the client but not the server, a
server-authoritative permission check is worthless. **Verify this with the first
override that exists**, before building anything on top of it. Check the server
log's mount line after deploying, and confirm the behaviour changes on a server
the client did not decide for itself.

### 2.0c - Is "Add call to parent function" available?

Right-click in the override graph and look for **Add call to parent function**.

- **Available** -> use it. Our check becomes `Parent result AND our rank check`,
  which preserves every vanilla rule we do not know about.
- **Not available** -> we would be replacing Funcom's logic wholesale, inheriting
  responsibility for ownership, locks, admin bypass and anything else it does.
  That is a much larger and riskier change, and worth reconsidering the hook.

---

## The slice itself

### 1. `BPL_GuildAccess.MeetsRankRequirement`

One pure function, the only place ranks are ever compared:

    Inputs:   Rank (ERank), Required (ERank)
    Output:   bool

    if Rank == ERank::InvalidRank  -> return false     // no guild, always deny
    return Rank >= Required

The `InvalidRank` test comes first and is not optional. See DESIGN.md section 1:
`InvalidRank` is hidden from the Switch node, so it lies outside 0-4 and may well
be 255, in which case a bare `>=` would grant guildless players access to
everything.

Delete the `Scratch` function while you are in there.

### 2. `BPL_GuildAccess.GetPawnRank`

    Input:    Pawn
    Output:   ERank

    Cast to Conan Character   -> on failure return InvalidRank
    GetGuild                  -> if null return InvalidRank
    GetCharacterUniqueID
    Guild.GetPlayerRank(id)   -> return it

Every failure path returns `InvalidRank`, so a thrall, a pet or a guildless
player all fail closed rather than falling through.

### 3. Override `CanAccessContainer` on `BP_PlaceableItemContainer`

    Parent: CanAccessContainer(InteractingPawn)  -> vanilla CanAccess
    GetPawnRank(InteractingPawn)                 -> rank
    MeetsRankRequirement(rank, <hardcoded>)      -> allowed

    CanAccess = vanilla AND allowed

Pass the other two outputs (`ContainerIsLocked`, `InstigatorIsOwner`) straight
through from the parent unchanged.

Hardcode the required rank for now. Making it configurable is step 5.

### 4. Prove it

Per TESTING.md, without a second account:

1. Hardcode required rank = `ERank_MAX` (4). As GuildMaster (3) you must be
   **denied**. The container must not open - not merely look different.
2. Hardcode it to `Recruit` (0). You must be allowed.
3. Leave your clan. With required rank at `Recruit`, you must still be **denied**,
   because `GetPawnRank` returns `InvalidRank`. **This is the most important
   test in the slice** - it is the security hole the design nearly shipped.
4. Have a thrall interact with the container. The cast fails, so it must deny.

Check the **server** log each time, not the client's.

### 5. Make the threshold configurable

Step 4 requires flipping the required rank repeatedly, and a full recook per flip
is 48 seconds plus two restarts. Move it to something changeable without a
rebuild - a server INI value or an admin command.

`BP_ServerSettings_C` appears in `BP_PlaceableItemContainer`'s imports and is
the first place to look.

---

## Done when

- A container refuses to open at a rank threshold above yours, verified in the
  server log.
- A guildless character is refused.
- A thrall is refused.
- Removing the hardcoded threshold restores vanilla behaviour exactly.

Then, and only then, Phase 3 adds per-object persistence.
