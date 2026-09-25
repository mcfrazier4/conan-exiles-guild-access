"""READ-ONLY: ActivateModule pins, checkmark texture sizes, GetRankName/RankToText signatures, RankToText call sites, W_GuildView root overlay."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
gv = unreal.load_asset("/Game/UI/Widgets/Guild/W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
sec("ActivateModule / GenerateLeaveGuildPopup nodes")
for n in ed.list_all_nodes():
    if title(n) in ("ActivateModule", "GenerateLeaveGuildPopup", "SetClanName"):
        print(f"   {title(n)}:", [(str(PL.get_pin_name(p)), (PL.get_pin_value(p) or '')[:80], [title(PL.get_owning_node(c)) for c in PL.list_connected_pins(p)]) for p in lib.list_all_pins(n)])
sec("textures")
for p in ("/Game/UI/Textures/Components/T_Checkmark", "/Game/UI/Textures/Icons/Overlays/T_UI_ico_Checkmark", "/Game/UI/Textures/Widgets/Checkbox/T_UI_Checkbox_Checked", "/Game/UI/Textures/GUIs/Guild/T_EditButton", "/Game/UI/Textures/GUIs/Guild/T_BgPanel", "/Game/UI/Textures/GUIs/Guild/T_BgEdit"):
    t = unreal.load_asset(p); print(f"   {p.split('/')[-1]}: {t.blueprint_get_size_x()}x{t.blueprint_get_size_y()}" if t else f"   {p}: MISSING")
sec("W_Guild_NamePopup tree (background / layout)")
OUT = r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad"
a = unreal.load_asset("/Game/UI/Widgets/Guild/W_Guild_NamePopup"); fn = os.path.join(OUT, "W_Guild_NamePopup.t3d")
task = unreal.AssetExportTask(); task.set_editor_property("object", a); task.set_editor_property("filename", fn); task.set_editor_property("automated", True); task.set_editor_property("replace_identical", True); task.set_editor_property("prompt", False); task.set_editor_property("exporter", unreal.ObjectExporterT3D())
print("   export:", unreal.Exporter.run_asset_export_task(task))
sec("BPL RankToText / ModController GetRankName signatures")
for p, fn_ in ((f"{LOCAL}/BPL_GuildAccess", "RankToText"), (f"{LOCAL}/BP_GA_ModController", "GetRankName"), (f"{LOCAL}/BPL_GuildAccess", "GetGAController")):
    bp = unreal.load_asset(p); g = GE.get_graph_editor_by_name(bp, fn_)
    for n in g.list_all_nodes():
        if n.get_class().get_name() in ("K2Node_FunctionEntry", "K2Node_FunctionResult"): print(f"   {fn_} {n.get_class().get_name()}: {pins(n)}")
sec("RankToText call sites in the leaf overrides")
for p in ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", "/Game/Systems/Building/Placeables/BP_PL_Door", "/Game/Systems/Building/BP_BuildDoor"):
    bp = unreal.load_asset(p)
    for g in lib.list_graph_names(bp):
        e = GE.get_graph_editor_by_name(bp, str(g))
        if not e: continue
        hits = [n for n in e.list_all_nodes() if title(n) == "RankToText"]
        if hits: print(f"   {p.split('/')[-1]}::{g}: {len(hits)} RankToText -> consumers {[[title(PL.get_owning_node(c)) for q in lib.list_output_pins(n) for c in PL.list_connected_pins(q)] for n in hits]}")
sec("done (read-only)")
