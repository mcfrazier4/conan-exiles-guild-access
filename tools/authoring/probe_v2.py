"""READ-ONLY v2 probe: guild API surface, dismantle/pick-up/repair hook points,
ModController persistence flags, clan-tab widget, rank badge textures. Saves nothing."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def methods(cls, pat=".", base=unreal.Object):
    b=set(dir(base)); rx=re.compile(pat, re.I)
    return [d for d in dir(cls) if not d.startswith("_") and d not in b and rx.search(d)]
def doc(cls, fn):
    f=getattr(cls, fn, None); return (f.__doc__ or "").strip().replace("\n", " ")[:200] if f else ""
def dump_node(n):
    print(f"   NODE [{n.get_class().get_name()}] {title(n)!r}")
    for p in lib.list_all_pins(n):
        d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
        v = PL.get_pin_value(p); conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
        if v or conns: print(f"      {d} {str(PL.get_pin_name(p)):24} val={v[:60]!r} -> {conns}")

sec("1. guild API: classes and rank/permission-related functions")
for cname in [c for c in dir(unreal) if re.match(r"(Guild|Clan)", c)]:
    c = getattr(unreal, cname)
    ms = methods(c, r"(rank|permission|allow|can_|owner|leader|officer|promote|demote|kick|invite|name|motd|member|stable)")
    if ms: print(f"   {cname}: {ms}")
for fn in ("get_player_rank", "set_player_rank", "get_guild_name", "get_owner", "is_owner", "can_kick", "can_invite", "get_members"):
    for cname in ("Guild", "GuildManager"):
        c = getattr(unreal, cname, None)
        if c and hasattr(c, fn): print(f"   --- {cname}.{fn}: {doc(c, fn)}")
print("   ERank:", [x for x in dir(getattr(unreal, "ERank", object)) if x.isupper()] if hasattr(unreal, "ERank") else "no unreal.ERank")

sec("2. ModController persistence flags (CDO)")
mc = unreal.load_asset(f"{LOCAL}/BP_GA_ModController")
cdo = unreal.get_default_object(lib.generated_class(mc))
pc = cdo.get_editor_property("persistence_component")
print("   persistence_component:", pc)
if pc:
    for prop in ("save_frequency", "save_on_spawn", "skip_saving", "is_client_only"):
        try: print(f"      {prop} = {pc.get_editor_property(prop)}")
        except Exception as e: print(f"      {prop}: {type(e).__name__}")
print("   ModController vars:", [str(v) for v in lib.list_member_variable_names(mc)])
print("   map/array pin types available:", bool(getattr(lib, "get_map_type", None)), bool(getattr(lib, "get_array_type", None)))

sec("3. placeables: dismantle / pick-up / move / repair hook points (Master)")
master = unreal.load_asset("/Game/Systems/Building/Placeables/BP_Master_Placeables")
for g in ("MasterPlaceables_HandleDismantling", "MasterPlaceables_HandleReturnToInventory", "MasterPlaceables_HandlePlaceableMovement", "MasterPlaceables_ConstructionModeRemove"):
    ed = GE.get_graph_editor_by_name(master, g)
    if not ed: print("   no graph", g); continue
    print(f"   --- {g}")
    for n in ed.list_all_nodes():
        k = n.get_class().get_name(); t = title(n)
        if k in ("K2Node_Message", "K2Node_CustomEvent", "K2Node_CallFunction") and any(s in t for s in ("Controller_", "Server", "Dismantle", "Demolish", "Destroy", "Return", "Move", "Pick", "Repair", "Interact Menu", "InteractMenu", "AddItem", "IsOwner", "CanIgnore")):
            dump_node(n)
ed = GE.get_graph_editor_by_name(master, "EventGraph")
print("   --- EventGraph: server-side dismantle/return events")
for n in ed.list_all_nodes():
    t = title(n)
    if n.get_class().get_name() in ("K2Node_CustomEvent", "K2Node_Event") and any(s in t for s in ("Dismantle", "Demolish", "Destroy", "Return", "Refund", "Move", "Repair", "TryReturn")):
        dump_node(n)

sec("4. building pieces: BP_BuildingBase menu / dismantle / repair")
bb = unreal.load_asset("/Game/Systems/Building/BP_BuildingBase")
print("   BuildingBase C++ methods (dismantle/repair/upgrade/owner):", methods(unreal.BuildingBase, r"(dismantle|demolish|repair|upgrade|owner|can_|interact|remove|destroy)", unreal.Actor))
print("   BuildableBase C++ methods:", methods(unreal.BuildableBase, r"(dismantle|demolish|repair|upgrade|can_|remove|destroy|pick)", unreal.Actor))
for g in [str(x) for x in lib.list_graph_names(bb)]:
    e = GE.get_graph_editor_by_name(bb, g)
    if not e: continue
    hits = [n for n in e.list_all_nodes() if any(s in title(n) for s in ("Dismantle", "Demolish", "Repair", "Upgrade", "Controller_", "AddItem", "InteractableMenu"))]
    if hits:
        print(f"   --- {g}")
        for n in hits: dump_node(n)
door = unreal.load_asset("/Game/Systems/Building/BP_BuildDoor")
for cname in ("BP_BuildingBase", "BP_BuildDoor"):
    bp = bb if cname == "BP_BuildingBase" else door
    print(f"   {cname} events:", [str(e.name) for e in lib.list_events(bp) if not e.is_implemented and re.search("Menu|Dismantle|Repair|Upgrade|Interact", str(e.name))])

sec("5. clan tab widget + rank badge textures (asset registry)")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(package_paths=["/Game/UI", "/Game/Systems/UI", "/Game/Systems/Guild", "/Game/Systems/Clan"], recursive_paths=True)
hits = []
for a in ar.get_assets(flt):
    nm = str(a.package_name); cls = str(a.asset_class_path.asset_name) if hasattr(a, "asset_class_path") else ""
    if re.search(r"(Clan|Guild|Rank)", nm, re.I): hits.append((nm, cls))
for h in sorted(hits)[:80]: print("   ", h)
flt2 = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Texture2D")], package_paths=["/Game"], recursive_paths=True)
tex = [str(a.package_name) for a in ar.get_assets(flt2) if re.search(r"(Rank|Chevron|Guild|Clan)", str(a.package_name), re.I)]
print("   textures:", sorted(tex)[:40])
sec("done (read-only)")
