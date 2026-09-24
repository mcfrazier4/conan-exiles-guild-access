"""READ-ONLY: every event/function the building-piece classes let a Blueprint override,
plus what BuildDoorFrame knows about its socketed door. Saves nothing."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
bb = unreal.load_asset("/Game/Systems/Building/BP_BuildingBase")
frame = unreal.load_asset("/Game/Systems/Building/BP_BuildDoorFrame")
sec("BP_BuildingBase: ALL overridable events (not implemented)")
print("  ", sorted(str(e.name) for e in lib.list_events(bb) if not e.is_implemented))
sec("BP_BuildingBase: ALL functions visible for override (list_functions)")
print("  ", sorted(str(f.name) for f in lib.list_functions(bb)))
sec("BuildingBase / BuildableBase C++: everything not on Actor")
base = set(dir(unreal.Actor))
print("   BuildingBase:", sorted(d for d in dir(unreal.BuildingBase) if not d.startswith("_") and d not in base))
print("   BuildableBase:", sorted(d for d in dir(unreal.BuildableBase) if not d.startswith("_") and d not in base))
sec("BuildSystemComponent.is_building_removal_allowed")
f = getattr(unreal.BuildSystemComponent, "is_building_removal_allowed", None)
print("  ", (f.__doc__ or "").strip().replace("\n", " ")[:400] if f else "MISSING")
sec("BP_BuildDoorFrame: graphs / variables / anything about the socketed door")
if frame:
    print("   graphs:", [str(g) for g in lib.list_graph_names(frame)])
    print("   variables:", [str(v) for v in lib.list_member_variable_names(frame)])
    ed = GE.get_graph_editor_by_name(frame, "EventGraph")
    for n in ed.list_all_nodes():
        if re.search(r"Door|Socket|Child|Attach", title(n)): print("   NODE", repr(title(n)))
sec("done (read-only)")
