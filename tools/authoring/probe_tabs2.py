"""READ-ONLY: W_FCEditableTextBlock API; nodes needed for the tab-bar rework; SignalClosing assign on W_GuildView."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
sec("W_FCEditableTextBlock / W_FCMultiLineEditableTextBox")
for p in ("/Game/UI/Framework/W_FCEditableTextBlock", "/Game/UI/Framework/W_FCMultiLineEditableTextBox"):
    bp = unreal.load_asset(p); print("  ", p.split("/")[-1], "parent:", lib.get_blueprint_parent_class(bp).get_name(), "graphs:", [str(g) for g in lib.list_graph_names(bp)], "dispatchers:", [str(d) for d in lib.list_event_dispatchers(bp)])
    print("     own vars:", [str(v) for v in lib.list_member_variable_names(bp) if not str(v).startswith("/Script/")])
uw = set(dir(unreal.UserWidget))
for cname in [c for c in dir(unreal) if re.search(r"EditableText", c) and isinstance(getattr(unreal, c, None), type) and issubclass(getattr(unreal, c), unreal.UserWidget)]:
    print(f"   C++ {cname}: {[d for d in dir(getattr(unreal, cname)) if not d.startswith('_') and d not in uw]}")
sec("nodes on W_GuildView")
gv = unreal.load_asset("/Game/UI/Widgets/Guild/W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
print("   self-context (closing/opened/tab):", [a for a in available(ed, []) if re.search(r"SignalClosing|SignalOpened|Closing|Assign.*Clos", a)][:10])
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed2 = GE.get_graph_editor_by_name(w, "EventGraph")
grid = ed2.add_get_member_variable_node("PermGrid"); gp = lib.list_output_pins(grid)[0]
print("   on PermGrid pin (slot):", [a for a in available(ed2, [gp]) if re.search(r"SlotAs|Slot as|GetParent|Get Parent", a)][:10])
print("   struct makes:", [a for a in available(ed2, []) if re.search(r"MakeAnchors|MakeMargin|MakeSlateChildSize|Make Anchors|Make Margin|Make Slate Child Size", a)][:10])
ed2.remove_nodes([grid])
sec("done (read-only)")
sec("W_Carousel (top nav) export + tab button classes")
OUT = r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad"
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/UI/HUD/Carousel", recursive=True):
    p = str(a.package_name); bp = unreal.load_asset(p)
    if not bp or not isinstance(bp, unreal.Blueprint): print("   ", p, "(not a BP)"); continue
    print("   ", p, "parent:", lib.get_blueprint_parent_class(bp).get_name(), "own vars:", [str(v) for v in lib.list_member_variable_names(bp) if not str(v).startswith("/Script/")][:12])
    fn = os.path.join(OUT, p.split("/")[-1] + ".t3d"); task = unreal.AssetExportTask(); task.set_editor_property("object", bp); task.set_editor_property("filename", fn); task.set_editor_property("automated", True); task.set_editor_property("replace_identical", True); task.set_editor_property("prompt", False); task.set_editor_property("exporter", unreal.ObjectExporterT3D())
    print("      export:", unreal.Exporter.run_asset_export_task(task))
sec("done (read-only)")
