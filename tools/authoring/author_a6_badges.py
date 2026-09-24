"""A6 - rank badges on the radial 'Set Access Rank' sub-items (Master + BuildDoor).
Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent: rewrites the four AddSubItem icon literals."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
BADGES = ["T_Rank_Recruit", "T_Rank_Member", "T_Rank_Officer", "T_Rank_GuildMaster"]
LABELS = ["Recruit", "Member", "Officer", "Guild Master"]
TARGETS = [("/Game/Systems/Building/Placeables/BP_Master_Placeables", os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_Master_Placeables.uasset")),
           ("/Game/Systems/Building/BP_BuildDoor", os.path.join(DISK_CONTENT, r"Systems\Building\BP_BuildDoor.uasset"))]
sec(f"mode = {MODE}")
wait_registry()
for b in BADGES: check(unreal.load_asset(f"/Game/UI/Textures/GUIs/Guild/{b}") is not None, f"texture {b}")
for path, disk in TARGETS:
    bp = unreal.load_asset(path); check(bp is not None, f"loaded {path}")
    ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    subs = nodes_titled(ed, "AddSubItem")
    check(len(subs) == 4, f"{path.split('/')[-1]}: four AddSubItem nodes ({len(subs)})")
    changed = 0
    for n in subs:
        label = PL.get_pin_value(lib.find_input_pin(n, "label")) or ""
        idx = next((i for i, l in enumerate(LABELS) if f'"{l}"' in label), None)
        if idx is None: check(False, f"unrecognised sub-item label {label[:60]!r}"); continue
        icon = f"/Game/UI/Textures/GUIs/Guild/{BADGES[idx]}.{BADGES[idx]}"
        if PL.get_pin_value(lib.find_input_pin(n, "icon")) == icon: print(f"   {LABELS[idx]}: already {BADGES[idx]}"); continue
        setval(n, "icon", icon, f"{LABELS[idx]} icon -> {BADGES[idx]}"); changed += 1
    compile_ok(bp, [(ed, "EventGraph")], path.split("/")[-1])
    if MODE == "real" and not failures and changed: save(bp, disk, path.split("/")[-1])
result()
