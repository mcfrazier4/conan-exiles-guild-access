"""READ-ONLY: can we make a K2Node_CallParentFunction headlessly? Saves nothing."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
bp = unreal.load_asset("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer")
ed = GE.get_graph_editor_by_name(bp, "EventGraph")
print("   K2Node_CallParentFunction in unreal:", hasattr(unreal, "K2Node_CallParentFunction"))
print("   retarget_node_class doc:", (GE.retarget_node_class.__doc__ or "").strip().replace("\n", " ")[:400])
n = ed.add_call_function_node("/Game/Systems/Building/Placeables/BP_Master_Placeables.BP_Master_Placeables_C:InteractableMenu")
print("   call node:", (n.get_class().get_name(), title(n), pins(n)) if n else None)
if n and hasattr(unreal, "K2Node_CallParentFunction"):
    try:
        r = ed.retarget_node_class(n, unreal.K2Node_CallFunction, unreal.K2Node_CallParentFunction)
        print("   retarget ->", r, "| node now:", (r.get_class().get_name(), title(r), pins(r)) if isinstance(r, unreal.Object) else "")
    except Exception as e: print("   retarget raised", type(e).__name__, str(e)[:200])
    for x in ed.list_all_nodes():
        if x.get_class().get_name() == "K2Node_CallParentFunction": print("   found parent-call node:", title(x), pins(x))
    print("   compile after retarget ->", lib.compile_blueprint(bp), "errors:", [(title(e), getattr(e, "error_msg", "")) for e in ed.list_nodes_with_errors()])
# how does the vanilla PL_Door express its parent call?
door = unreal.load_asset("/Game/Systems/Building/Placeables/BP_PL_Door")
ded = GE.get_graph_editor_by_name(door, "EventGraph")
for x in ded.list_all_nodes():
    if x.get_class().get_name() == "K2Node_CallParentFunction": print("   PL_Door parent-call node:", title(x), pins(x))
print("   names with 'parent' (no ctx):", [a for a in available(ed, [], "parent")][:15])
sec("done (read-only)")
