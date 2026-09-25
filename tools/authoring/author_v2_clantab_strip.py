"""Remove the PreConstruct ButtonData append from the W_GuildView override (the bar builds before it runs);
the 'Ranks' entry is added in the designer instead. Keeps the switch pin 2 -> request wiring."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
GV_PATH = "/Game/UI/Widgets/Guild/W_GuildView"; GV_DISK = os.path.join(DISK_CONTENT, r"UI\Widgets\Guild\W_GuildView.uasset")
sec(f"mode = {MODE}")
wait_registry()
gv = unreal.load_asset(GV_PATH); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
victims = [n for n in ed.list_all_nodes() if title(n) in ("MakeButtonBarData", "Add", "Get ButtonData", "Get ButtonBar", "Get RanksAdded", "Set RanksAdded", "Event Pre Construct") or (n.get_class().get_name() == "K2Node_IfThenElse" and any(title(PL.get_owning_node(c)) == "Get RanksAdded" for c in PL.list_connected_pins(lib.find_condition_pin(n))))]
seqs = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_ExecutionSequence" and any(title(PL.get_owning_node(c)) == "Event Pre Construct" for c in PL.list_connected_pins(exec_in(n)))]
for s in seqs:
    t0 = list(PL.list_connected_pins(pin_exact_out(s, "then_0"))); ev = [PL.get_owning_node(c) for c in PL.list_connected_pins(exec_in(s))]
    if t0 and ev: PL.break_pin_links(exec_in(s)); connect(then_out(ev[0]), t0[0], "PreConstruct -> original chain")
    victims.append(s)
print("   removing:", sorted(set(title(n) for n in victims)))
ed.remove_nodes([n for n in victims if title(n) != "Event Pre Construct" or not list(PL.list_connected_pins(then_out(n)))])
try: ed.remove_member_variable("RanksAdded"); print("   RanksAdded removed")
except Exception as e: print("   RanksAdded:", type(e).__name__)
compile_ok(gv, [(ed, "EventGraph")], "W_GuildView")
print("   switch wiring intact:", bool(nodes_titled(ed, "Server_ServerRequestClanTable")))
if MODE == "real" and not failures: save(gv, GV_DISK, "W_GuildView override")
result()
