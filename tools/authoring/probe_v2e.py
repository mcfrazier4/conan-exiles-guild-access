"""READ-ONLY: verify the GUI session (widget skeleton, RPC flags via names, parent calls)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks")
print("   widget:", w, "| parent:", lib.get_blueprint_parent_class(w) if w else None)
if w:
    print("   widget variables:", [str(v) for v in lib.list_member_variable_names(w)])
    print("   widget graphs:", [str(g) for g in lib.list_graph_names(w)], "| events:", [str(e.name) for e in lib.list_events(w) if e.is_implemented])
    ed = GE.get_graph_editor_by_name(w, "EventGraph")
    print("   available: SetText(TextBlock):", available(ed, [], "SetText")[:6])
    print("   available: OnClicked/OnTextCommitted:", available(ed, [], "AssignOnClicked")[:3], available(ed, [], "AssignOnTextCommitted")[:3])
pl = unreal.load_asset(f"{LOCAL}/BPC_GA_Player")
print("   player events:", [str(e.name) for e in lib.list_events(pl) if e.is_implemented])
for path in ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", "/Game/Systems/Building/Placeables/BP_PL_Door"):
    bp = unreal.load_asset(path); ed = GE.get_graph_editor_by_name(bp, "GetCanBeDismantled")
    print(f"   {path.split('/')[-1]} GetCanBeDismantled parent node:", bool(nodes_titled(ed, "Parent: GetCanBeDismantled")))
