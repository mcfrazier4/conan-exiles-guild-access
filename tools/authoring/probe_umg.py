"""READ-ONLY-ish: can a WidgetBlueprint and its widget tree be authored headlessly?
Creates a transient asset in memory and never saves it."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
sec("factory / classes")
print("   WidgetBlueprintFactory:", hasattr(unreal, "WidgetBlueprintFactory"), "| WidgetBlueprint:", hasattr(unreal, "WidgetBlueprint"), "| WidgetTree:", hasattr(unreal, "WidgetTree"))
print("   UniformGridPanel:", hasattr(unreal, "UniformGridPanel"), "| CheckBox:", hasattr(unreal, "CheckBox"), "| TextBlock:", hasattr(unreal, "TextBlock"), "| EditableTextBox:", hasattr(unreal, "EditableTextBox"))
bp = None
try:
    f = unreal.WidgetBlueprintFactory()
    try: f.set_editor_property("parent_class", unreal.UserWidget)
    except Exception as e: print("   parent_class:", type(e).__name__, str(e)[:80])
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ZZ_ProbeWidget", LOCAL, unreal.WidgetBlueprint, f)
    print("   created:", bp)
except Exception as e: print("   create raised", type(e).__name__, str(e)[:160])
if bp:
    try:
        tree = bp.get_editor_property("widget_tree"); print("   widget_tree:", tree)
        root = tree.get_editor_property("root_widget"); print("   root_widget:", root)
        canvas = unreal.new_object(unreal.CanvasPanel, outer=tree, name="RootCanvas")
        tree.set_editor_property("root_widget", canvas); print("   root set ->", tree.get_editor_property("root_widget"))
        grid = unreal.new_object(unreal.UniformGridPanel, outer=tree, name="PermGrid")
        slot = canvas.add_child(grid); print("   add_child(grid) ->", slot)
        txt = unreal.new_object(unreal.TextBlock, outer=tree, name="Header_0"); txt.set_text(unreal.Text("Recruit"))
        gs = grid.add_child_to_uniform_grid(txt, 0, 1); print("   add_child_to_uniform_grid ->", gs)
        cb = unreal.new_object(unreal.CheckBox, outer=tree, name="Cell_0_0"); grid.add_child_to_uniform_grid(cb, 1, 1)
        print("   children:", [c.get_name() for c in grid.get_all_children()])
        print("   compile ->", lib.compile_blueprint(bp))
        print("   variables after compile:", [str(v) for v in lib.list_member_variable_names(bp)][:10])
        for w in (txt, cb):
            try: w.set_editor_property("is_variable", True)
            except Exception as e: print("   is_variable:", type(e).__name__, str(e)[:80])
        print("   compile2 ->", lib.compile_blueprint(bp), "vars:", [str(v) for v in lib.list_member_variable_names(bp)][:10])
        ed = GE.get_graph_editor_by_name(bp, "EventGraph"); print("   graphs:", [str(g) for g in lib.list_graph_names(bp)], "| events:", [str(e.name) for e in lib.list_events(bp) if e.is_implemented])
    except Exception as e: print("   tree authoring raised", type(e).__name__, str(e)[:200])
sec("CreateWidget / AddToViewport node availability (in BPC_GA_Player graph)")
pl = unreal.load_asset(f"{LOCAL}/BPC_GA_Player"); ped = GE.get_graph_editor_by_name(pl, "EventGraph")
for nm in ("Create Widget", "CreateWidget", "AddtoViewport", "RemovefromParent", "SetInputMode"):
    print(f"   {nm}:", available(ped, [], nm)[:4])
sec("done (transient asset not saved)")
