"""READ-ONLY: where does 'Container is locked!' come from? Saves nothing."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
for path in ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", "/Game/Systems/Building/Placeables/BP_Master_Placeables"):
    bp = unreal.load_asset(path)
    sec(path)
    for g in lib.list_graph_names(bp):
        ed = GE.get_graph_editor_by_name(bp, str(g))
        if ed is None: continue
        for n in ed.list_all_nodes():
            t = title(n)
            hit = False
            for p in lib.list_all_pins(n):
                v = PL.get_pin_value(p) or ""
                if "locked" in v.lower() or "lock" in t.lower() and "Notification" in t: hit = True
            if hit or ("Notification" in t or "MessageBox" in t or "ShowMessage" in t or "CanAccessContainer" in t):
                print(f"   [{g}] NODE [{n.get_class().get_name()}] {t!r}")
                for p in lib.list_all_pins(n):
                    d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
                    conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
                    v = PL.get_pin_value(p)
                    if v or conns: print(f"         {d} {str(PL.get_pin_name(p)):22} val={v[:90]!r} -> {conns}")
sec("done (read-only)")
