"""READ-ONLY: W_Guild_NamePopup API and how W_GuildView opens it and receives the new name."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
uw = set(dir(unreal.UserWidget))
bp = unreal.load_asset("/Game/UI/Widgets/Guild/W_Guild_NamePopup"); par = lib.get_blueprint_parent_class(bp)
print("   parent:", par.get_name(), "graphs:", [str(g) for g in lib.list_graph_names(bp)], "dispatchers:", [str(d) for d in lib.list_event_dispatchers(bp)])
print("   own vars:", [str(v) for v in lib.list_member_variable_names(bp) if not str(v).startswith("/Script/")])
c = getattr(unreal, par.get_name(), None)
if c: print("   C++:", [d for d in dir(c) if not d.startswith("_") and d not in uw and not d.startswith("key_nav")])
for g in lib.list_graph_names(bp):
    ed = GE.get_graph_editor_by_name(bp, str(g))
    if ed: print(f"   {g}:", sorted(set(title(n) for n in ed.list_all_nodes()))[:40])
sec("W_GuildView: nodes around the name popup")
gv = unreal.load_asset("/Game/UI/Widgets/Guild/W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
for n in ed.list_all_nodes():
    t = title(n)
    if re.search(r"NamePopup|OpenPopUp|Open Pop|CreateDelegate|Create Event|SignalNameChanged|UpdateGuildName|Bind|Assign|ButtonEditClanName", t):
        print(f"   [{n.get_class().get_name()}] {t}: ", [(str(PL.get_pin_name(p)), (PL.get_pin_value(p) or '')[:60], [title(PL.get_owning_node(c)) for c in PL.list_connected_pins(p)]) for p in lib.list_all_pins(n)])
sec("done (read-only)")
