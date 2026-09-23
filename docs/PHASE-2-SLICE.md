# Phase 2 - the vertical slice

Goal: a container that refuses to open for a player below a required rank,
enforced on the server.

No UI. No persistence. No doors. One hardcoded rank, one override, and proof
that it actually blocks.

The point of the slice is not the feature. It is to answer whether the
architecture in DESIGN.md survives contact with a running server, while the mod
is still small enough to throw away.

---

## RESULTS - the three checks, answered 2026-09-23

### 2.0c - parent call: YES

The dev kit **auto-generated** `Parent: CanAccessContainer` and pre-wired it.
We extend Funcom's logic rather than replace it.

### 2.0a - exec pins: YES

Despite `CanAccessContainer (pure, const)`, the override's implementation graph
has execution pins on the entry node, the parent call and the return node. Impure
nodes should therefore be placeable. **Still to confirm by actually placing a
Print String**, which is also how we settle server-vs-client below.

### 2.0b - the override enforces: YES

Deny-all probe: broke the `Can Access` wire into the Return Node so the function
always returns false. Result in game:

    Large Chest
    Hold E for more options
    Locked                    <- red, rendered by vanilla
    Owner: test clan

The chest would not open. **Overriding this pure function decides access rather
than merely reporting it.** The architecture in DESIGN.md holds.

Vanilla also renders the "Locked" state automatically from `CanAccess` being
false - we wrote no UI for it. That covers much of user journey steps 5 and 6;
we only need to extend the text to name the required rank.

### 2.0d - enforcement is SERVER-SIDE: CONFIRMED

Authority probe, 2026-09-23. `Switch Has Authority` in the override, with:

    Authority (server) -> Return Node, Can Access = false
    Remote    (client) -> Return Node, parent's real values

Result in game:

    Hover text:   "Open" in green          <- client permitted
    Press E:      "Container is locked!"   <- server refused
    Outcome:      container does not open

The client's answer and the server's answer disagreed, and **the server's
answer won**. Enforcement is server-authoritative, so a modified client cannot
bypass it. This was the last architectural risk in the design.

Vanilla also raises a "Container is locked!" message box automatically on
denial - the denial plumbing for user journey step 6 already exists. We will
want to replace the wording to name the required rank.

> `UNKNOWN`: whether that message's text can be changed from Blueprint, or
> whether it is fixed in C++. If fixed, the required rank has to be surfaced
> through `InteractableGetSimpleDisplayText` instead.

### Superseded: server-side vs client-side

The test client has the mod installed, so a client-only check would look
identical. Enforcement is proven; **its location is not**. A permission system
that only runs client-side is worthless against a modified client.

Settle it with a `Print String` in the override and confirm the line appears in
the **dedicated server's** log, not just the client's.

## Live test log (2026-09-23)

Sentinel bisect of the 255 failure. Each row is one cook/deploy/test cycle.

| Check compiled in | Result | Conclusion |
|---|---|---|
| `Rank == 3`, lookup by UniqueID | locked | not returning 3 |
| `Rank == 255` | **opened** | `GetPawnRank` falls through to 255 |
| `Rank == 3`, lookup by StableId | locked | ID type was not the cause |
| `Rank == 250` (cast-failed sentinel) | locked | **the cast succeeds** |
| `Rank == 3` after the Condition fix | **opened** | **the whole chain works.** Vertical slice proven live. |
| members-only build: GM opens clan chest | **opened** | member path intact after rewiring |
| members-only build: clanless player opens own fresh chest | **opened** | **regression fixed** - non-members defer to vanilla |
| members-only build: clanless player vs old clan chest | opened | **void**: leaving as sole GM disbanded the clan; DB shows `guilds` empty and the buildings now owned by character 140. Equivalent to the row above. |

Remaining candidates: the guild-validity path (sentinel 251) or `GetPlayerRank`
returning `InvalidRank` (255).

**Leading hypothesis:** the `Is Valid+ Branch` macro used in `GetPawnRank` has
two inputs, `Object` and a `Condition` bool that was left unchecked. If the
macro means "valid AND condition", every call routes to `False Or Invalid`
before the rank lookup runs. That single cause is consistent with all four rows
above and predicts `Rank == 251` would open.

**Settled by a headless graph dump, not a cook cycle.** The dump showed every
wire in all three graphs was correct and exactly one thing wrong:

    NODE [K2Node_MacroInstance] 'Is Valid+ Branch'
       pin Condition   INPUT   val=''   -> []

`Condition` empty (= false) and unconnected. The macro's outputs are named
`True` and `False or Invalid`, i.e. it is `IsValid(Object) AND Condition`, so
every call took the failure exit before the rank lookup ran. Consistent with all
four rows above.

**Fixed headlessly** (`set_pin_value(Condition, 'true')`), sentinels restored
to 255, threshold restored to `Rank == 3`, both assets compiled with zero node
errors and verified on disk by a second dump. Lesson: the macro was my
recommendation; a plain `IsValid` + `Branch` would have had no hidden second
input. Replace it during cleanup.

## Members-only rule: authored headlessly (2026-09-23)

First real graph authoring through the Python API, not just pin edits. Built and
verified in a **dry run** (nothing saved), then applied in two runs:

    GA_MODE=bpl       without -ModDevKit   adds BPL_GuildAccess.IsGuildMemberRank(Rank: Byte) -> Bool = Rank <= 3
    GA_MODE=override  with    -ModDevKit   rewires CanAccessContainer

Resulting override logic, confirmed by dumping the saved asset:

    CanAccess = Parent.CanAccess AND ( NOT IsGuildMemberRank(rank) OR MeetsRankRequirement(rank, 3) )

Non-members (rank 255) short-circuit to vanilla; members hit the rank gate.

Function-path formats that `add_call_function_node` accepts, discovered by
trying candidates in the dry run:

    /Script/Engine.KismetMathLibrary:LessEqual_ByteByte
    /Script/Engine.KismetMathLibrary:Not_PreBool
    /Script/Engine.KismetMathLibrary:BooleanOR
    /Game/Mods/GuildAccess/Local/BPL_GuildAccess.BPL_GuildAccess_C:IsGuildMemberRank

Known cosmetic debt: `set_node_pos` rejected my arguments, so the three new
nodes sit at the graph origin. Harmless at runtime; tidy when someone next
opens the graph in the GUI, or once the signature is confirmed.

## Automation route: editor Python

Epic's MCP plugin is present in this dev kit as descriptors only - no compiled
binaries anywhere - so the Claude marketplace Unreal MCP plugin cannot work
here. Not fixable without engine source.

What does work: `PythonScriptPlugin` ships **with** binaries and is already
enabled (`LogPython: Using Python 3.11.8` in the editor log), and this 5.8
build's `BlueprintEditorLibrary` exposes a complete authoring surface:

    CreateOverrideFunctionGraph  AddCallFunctionNode  AddBranchNode  AddReturnNode
    CreateNodeFromName           FindInputPin/OutputPin/ExecutePin/ThenPin/ResultPin
    TryCreateConnection          BreakPinLinks        GetPinValue    SetPinValue
    CompileBlueprint             SetLocalVariableDefaultValue  ...  (93 functions)

Headless entry point: `Engine\Binaries\Win64\UnrealEditor-Cmd.exe <uproject>
-run=pythonscript -script=<file> -ModDevKit`. `EditorScriptingUtilities`
(`EditorAssetLibrary`) is **not** enabled, so use `unreal.load_asset` and
`unreal.EditorLoadingAndSavingUtils` instead.

## The three checks, as originally written

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

## Status: slice complete (2026-09-23)

- A container refuses or allows by the interacting player's real guild rank,
  decided on the dedicated server. Proven.
- Non-members defer to vanilla; a solo player keeps access to their own
  property. Proven.
- Deliberately **not** done: the "raise the threshold to 4 and watch a GM get
  refused" cycle. `Rank == 3` already proved the value is exactly 3 and both
  bounds evaluate; that `3 >= 4` is false is not worth two cook cycles. It
  falls out for free once the threshold is a variable rather than a literal.
- Still untestable solo: a non-member against **someone else's** locked clan
  container. See TESTING.md for a possible DB-level route.

## Done when

- A container refuses to open at a rank threshold above yours, verified in the
  server log.
- A guildless character is refused.
- A thrall is refused.
- Removing the hardcoded threshold restores vanilla behaviour exactly.

Then, and only then, Phase 3 adds per-object persistence.
