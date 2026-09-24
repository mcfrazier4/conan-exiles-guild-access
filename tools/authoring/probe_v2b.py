"""READ-ONLY v2 probe, part b: server-side dismantle/pick-up/repair hooks and clan widgets."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def methods(cls, pat=".", base=unreal.Object):
    b=set(dir(base)); rx=re.compile(pat, re.I)
    return [d for d in dir(cls) if not d.startswith("_") and d not in b and rx.search(d)]
def doc(cls, fn):
    f=getattr(cls, fn, None); return (f.__doc__ or "").strip().replace("\n", " ")[:220] if f else ""
def dump_graph(bp, g):
    ed = GE.get_graph_editor_by_name(bp, g)
    if not ed: print(f"   (no graph {g})"); return
    print(f"   --- {g}")
    for n in ed.list_all_nodes():
        k = n.get_class().get_name()
        if k in ("K2Node_Knot",): continue
        print(f"   NODE [{k}] {title(n)!r}")
        for p in lib.list_all_pins(n):
            d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
            v = PL.get_pin_value(p); conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
            if v or conns or k in ("K2Node_FunctionEntry", "K2Node_FunctionResult"): print(f"      {d} {str(PL.get_pin_name(p)):24} val={v[:60]!r} -> {conns}")

sec("1. overridable C++ hooks on the buildable classes (events + functions with Can/Dismantle/Repair/Remove/Return)")
for cname in ("BuildableBase", "PlaceableBase", "BuildingBase"):
    c = getattr(unreal, cname)
    print(f"   {cname}:", methods(c, r"(can_|dismantle|demolish|repair|upgrade|remove|return|pick|allow|permission|owner)", unreal.Actor))
master = unreal.load_asset("/Game/Systems/Building/Placeables/BP_Master_Placeables")
bb = unreal.load_asset("/Game/Systems/Building/BP_BuildingBase")
for nm, bp in (("Master", master), ("BuildingBase", bb)):
    print(f"   {nm} overridable events:", [str(e.name) for e in lib.list_events(bp) if not e.is_implemented and re.search("Can|Dismantle|Repair|Upgrade|Remove|Return|Allow|Interact", str(e.name))])
    print(f"   {nm} functions (Can*/Get*):", [str(f.name) for f in lib.list_functions(bp) if re.search("^(Can|Get|Does|Allow|Is)", str(f.name))])

sec("2. Master graphs that look like server-side gates")
for g in ("GetCanBeDismantled", "CanReturnToInventory", "CanIgnoreOwnership", "DoesPurgeAllowModifyingPlaceable", "GetIsLockable", "CanAccessPlaceableInventory", "InteractableCanBeLooted"):
    dump_graph(master, g)

sec("3. BuildSystemComponent: server functions")
for cname in [c for c in dir(unreal) if re.search(r"BuildSystem|BuildingSystem", c)]:
    c = getattr(unreal, cname)
    print(f"   {cname}:", methods(c, r"(server|dismantle|demolish|repair|upgrade|remove|return|move|allow|can_)", unreal.ActorComponent))
    for fn in methods(c, r"(server_dismantle|server_demolish|server_return|server_repair|server_upgrade|allow_movement)", unreal.ActorComponent)[:8]:
        print(f"      --- {fn}: {doc(c, fn)}")

sec("4. the 'Player Interactable ...' interface (who owns the dismantle RPC)")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")], package_paths=["/Game/Systems", "/Game/Characters"], recursive_paths=True)
for a in ar.get_assets(flt):
    pc = str(a.get_tag_value("ParentClass") or "")
    if "Interface" in pc and re.search(r"Player|Interact|Build|Character", str(a.package_name)):
        bp = unreal.load_asset(str(a.package_name))
        if not bp: continue
        fns = [str(g) for g in lib.list_graph_names(bp)]
        hits = [f for f in fns if re.search("Dismantle|Demolish|Return|Repair|Upgrade|SetLocked|Move", f)]
        if hits: print(f"   {a.package_name}: {hits}")

sec("5. clan widgets")
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/UMGEditor", "WidgetBlueprint")], package_paths=["/Game/UI/Widgets"], recursive_paths=True)
ws = sorted(str(a.package_name) for a in ar.get_assets(flt) if re.search(r"Guild|Clan|Rank|Roster|Member", str(a.package_name), re.I))
for w in ws: print("   ", w)
for w in ws:
    if re.search(r"(W_Guild|W_Clan)(View|Tab|Panel|Board)", w):
        bp = unreal.load_asset(w)
        if bp: print(f"   --- {w}: parent={lib.get_blueprint_parent_class(bp)} graphs={[str(g) for g in lib.list_graph_names(bp)][:20]} vars={[str(v) for v in lib.list_member_variable_names(bp)][:30]}")
sec("6. rank badge textures")
for r in ("Recruit", "Member", "Officer", "GuildMaster"):
    t = unreal.load_asset(f"/Game/UI/Textures/GUIs/Guild/T_Rank_{r}")
    print(f"   T_Rank_{r}: {t.get_class().get_name() if t else 'MISSING'} {t.blueprint_get_size_x() if t else ''}x{t.blueprint_get_size_y() if t else ''}")
sec("done (read-only)")
