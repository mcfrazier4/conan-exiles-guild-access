# GuildAccess — project context

A Conan Exiles Enhanced mod adding per-object access control for doors and
containers, gated on the player's clan rank.

## Decisions (locked 2026-09-22)

| Question | Decision |
|---|---|
| Rank source | Built-in 4 clan ranks (Recruit / Member / Officer / Leader). No custom rank registry. |
| Configuration | Per-object. The owner sets a required rank on each individual door/container. |
| Audience | Steam Workshop release. No shortcuts that would block a public release. |
| Owner's Unreal experience | None. Write editor instructions step by step, name panels and nodes explicitly, explain Blueprint concepts rather than assuming them. |

## Environment

- Game: Conan Exiles **Enhanced** (UE 5.6.1), Steam, `C:\Program Files (x86)\Steam\steamapps\common\Conan Exiles`
- Dev kit: **installed** at `C:\Program Files\Epic Games\CEUE5Devkit` (verified 2026-09-23)
  - Launch with `RunDevKit.bat` in that folder — it passes `-ModDevKit`, without which there is no mod menu
  - Project lives under `UE4\` despite being the UE5 kit; the folder name is a leftover
  - Path contains a space and is 38 chars. If cooking fails with path-related
    errors, create a short junction rather than reinstalling — see
    docs/PHASE-0-SETUP.md §1
- Repo: `E:\ClaudeCode\conan-exiles\guild-access`
- Mod name: `GuildAccess`

## Division of labour

Claude cannot drive the UE5 editor GUI. Claude handles architecture, logic
design, data tables, config, build scripts, docs, reading files off disk, and
debugging from pasted screenshots or copied Blueprint node text. The owner
handles all Blueprint graph editing and in-game testing.

## Build

Mod assets live in the repo at `GuildAccess/` and are exposed to the dev kit via
a directory junction (see docs/PHASE-0-SETUP.md), so git tracks the real assets.

    tools/build-mod.ps1

## House rules

- Every access check must be **server-authoritative**. A client-side check is
  decoration, not security.
- Minimise the base-asset override surface. Override the smallest possible
  function and immediately delegate to our own mod-owned Blueprint library.
- Mark anything unverified as `UNKNOWN` rather than guessing at asset or
  function names. Guessed names have cost us nothing yet; keep it that way.
