"""READ-ONLY: what BP_BuildDoor / BP_BuildingBase offer for a rank gate + menu. Saves nothing."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def dump_node(n, all_pins=False):
    print(f"   NODE [{n.get_class().get_name()}] {title(n)!r}")
    for p in lib.list_all_pins(n):
        d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
        v = PL.get_pin_value(p)
        conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
        if all_pins or v or conns: print(f"      {d} {str(PL.get_pin_name(p)):24} val={v[:70]!r} -> {conns}")
def walk(ed, start, maxn=30):
    ev = nodes_titled(ed, start)
    if not ev: print(f"   {start}: MISSING"); return
    seen=set(); q=[ev[0]]
    while q and len(seen)<maxn:
        n=q.pop(0); k=n.get_name()
        if k in seen: continue
        seen.add(k); dump_node(n)
        for p in lib.list_output_pins(n):
            for c in PL.list_connected_pins(p):
                if str(PL.get_pin_name(c)).lower() in ("execute","exec","then","in","input"): q.append(PL.get_owning_node(c))

for path in ("/Game/Systems/Building/BP_BuildingBase", "/Game/Systems/Building/BP_BuildDoor"):
    bp = unreal.load_asset(path)
    sec(path)
    if bp is None: print("   NOT FOUND at this path"); continue
    print("   parent:", lib.get_blueprint_parent_class(bp))
    print("   graphs:", [str(g) for g in lib.list_graph_names(bp)])
    print("   variables:", [str(v) for v in lib.list_member_variable_names(bp)])
    print("   implemented events:", [str(e.name) for e in lib.list_events(bp) if e.is_implemented])
    print("   overridable (not implemented) events mentioning Interact/Custom:", [str(e.name) for e in lib.list_events(bp) if not e.is_implemented and re.search("Interact|Custom|Activate|Use", str(e.name))])
    ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    if ed:
        for ev in ("Event InteractableMenu", "Event InteractableActivate", "Event Custom Interaction", "Event BeginPlay"):
            sec(f"{path.split('/')[-1]} :: {ev} chain"); walk(ed, ev, 25)
        sec(f"{path.split('/')[-1]} :: AddItem / Controller_ / Authority / notification nodes")
        for n in ed.list_all_nodes():
            t = title(n)
            if any(k in t for k in ("AddItem", "Controller_", "Authority", "Notification", "IsOwner", "SetDirty", "dirty", "Custom Interaction", "OpenDoor", "Open", "Toggle")) and n.get_class().get_name() != "K2Node_Knot":
                dump_node(n)
    for g in ("InteractableGetSimpleDisplayText", "InteractableDefaultAction", "ShouldDisableInteraction", "CanInteract"):
        e = GE.get_graph_editor_by_name(bp, g)
        if e:
            sec(f"{path.split('/')[-1]} :: {g}")
            for n in e.list_all_nodes(): dump_node(n, all_pins=True)
# asset registry: where are the door classes?
ar = unreal.AssetRegistryHelpers.get_asset_registry()
sec("assets named *BuildDoor* / *BuildingBase*")
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")], package_paths=["/Game/Systems/Building"], recursive_paths=True)
for a in ar.get_assets(flt):
    nm = str(a.package_name)
    if re.search(r"BuildDoor|BuildingBase|Door", nm) and "Trapdoor" not in nm: print("   ", nm, "parent:", str(a.get_tag_value("ParentClass") or "")[-60:])
sec("done (read-only)")
