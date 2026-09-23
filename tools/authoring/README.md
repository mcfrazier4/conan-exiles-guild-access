# Headless Blueprint authoring scripts

Run with `run_py.ps1 -Script <file> -Mode dry|real [-ModDevKit]` from this folder.
The dev kit GUI must be closed. `dry` builds everything in memory, compiles,
dumps the graphs and saves nothing; `real` saves and verifies file mtimes.

| Script | Layer flag | What it authors |
|---|---|---|
| `author_a1.py` | `-ModDevKit` | RequiredRank on Master, container reads it, placeable-door gate |
| `author_a2_bpl.py` | (none) | BPL_GuildAccess: RankToText, RankCanSetRequired |
| `author_a2_new.py` | `-ModDevKit` | BPC_GA_Lock, BPC_GA_Player, BP_GA_ModController |
| `author_a2_master.py` | `-ModDevKit` | Master: SCS lock component, server handler, radial menu, hover text |

All scripts are idempotent: re-running in `dry` mode against saved assets is
the verification step. See docs/AUTOMATION.md for the API notes.
