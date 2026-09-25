"""READ-ONLY: RankToText function graph and BPC_GA_Player event list (for BeginPlay)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
bp = unreal.load_asset(f"{LOCAL}/BPL_GuildAccess"); ed = GE.get_graph_editor_by_name(bp, "RankToText")
for n in ed.list_all_nodes():
    print(f"   [{n.get_class().get_name()}] {title(n)}:", [(str(PL.get_pin_name(p)), (PL.get_pin_value(p) or '')[:40], [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]) for p in lib.list_all_pins(n)])
sec("BPC_GA_Player events")
pl = unreal.load_asset(f"{LOCAL}/BPC_GA_Player"); ped = GE.get_graph_editor_by_name(pl, "EventGraph")
print("  ", [title(n) for n in ped.list_all_nodes() if n.get_class().get_name() in ("K2Node_Event", "K2Node_CustomEvent")])
print("   overridable:", [a for a in available(ped, []) if re.search(r"BeginPlay|Begin Play", a)][:5])
sec("done (read-only)")
