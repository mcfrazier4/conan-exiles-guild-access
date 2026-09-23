"""Retarget library call nodes in the container and door overrides from the
editor-only '/Game/Mods/GuildAccess/Local/BPL_GuildAccess' package to the runtime
name '/Game/Mods/GuildAccess/BPL_GuildAccess'. Run WITH -ModDevKit. GA_MODE=dry|real.

Every K2Node_CallFunction whose title is one of the library's functions is
recreated from the flattened path, its pins re-wired by name (links and literal
defaults), and the old node removed. Nodes already on the right package are
recreated too; that is harmless and keeps the script simple."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
TARGETS = [
    ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", ["CanAccessContainer"], os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset")),
    ("/Game/Systems/Building/Placeables/BP_PL_Door", ["EventGraph"], os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_PL_Door.uasset")),
]
sec(f"mode = {MODE}")
wait_registry()
bpl = unreal.load_asset(f"{LOCAL}/BPL_GuildAccess"); check(bpl is not None, "loaded BPL via flattened path")
LIB_FUNCS = {str(f.name) for f in lib.list_functions(bpl)}
print("   library functions:", sorted(LIB_FUNCS))

def retarget_node(ed, old):
    t = title(old)
    # snapshot pins
    snap = []
    for p in lib.list_all_pins(old):
        snap.append((str(PL.get_pin_name(p)), "INPUT" in str(PL.get_pin_direction(p)), PL.get_pin_value(p), list(PL.list_connected_pins(p))))
    new = ed.add_call_function_node(f"{BPL_C}:{t}")
    if not check(new is not None, f"recreate {t} from flattened path"): return
    for name, is_in, val, links in snap:
        np = lib.find_input_pin(new, name) if is_in else lib.find_output_pin(new, name)
        if np is None:
            check(False, f"{t}: pin {name} missing on new node"); continue
        if is_in and val and not links: PL.set_pin_value(np, val)
        for other in links:
            check(PL.try_create_connection(np, other), f"{t}.{name} -> {title(PL.get_owning_node(other))}.{PL.get_pin_name(other)}")
    ed.remove_nodes([old])

saved = []
for path, graphs, disk in TARGETS:
    sec(path)
    bp = unreal.load_asset(path); check(bp is not None, "loaded")
    eds = []
    for g in graphs:
        ed = GE.get_graph_editor_by_name(bp, g); eds.append((ed, g))
        victims = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_CallFunction" and title(n) in LIB_FUNCS]
        print(f"   {g}: retargeting {[title(n) for n in victims]}")
        for n in victims: retarget_node(ed, n)
        # literal class/object pin values that name the editor-only package
        for n in ed.list_all_nodes():
            for p in lib.list_input_pins(n):
                v = PL.get_pin_value(p)
                if v and "/GuildAccess/Local/" in v:
                    check(PL.set_pin_value(p, v.replace("/GuildAccess/Local/", "/GuildAccess/")), f"pin literal fixed on {title(n)}.{PL.get_pin_name(p)}")
        dump(ed, g)
    compile_ok(bp, eds, path.split("/")[-1])
    if MODE == "real" and not failures:
        save(bp, disk, path.split("/")[-1])
result()
