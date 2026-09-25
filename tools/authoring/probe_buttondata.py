"""READ-ONLY: can Python reach the W_GuildView override's ButtonBar.ButtonData in the widget tree?"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
gv = unreal.load_asset("/Game/UI/Widgets/Guild/W_GuildView")
for prop in ("widget_tree", "WidgetTree"):
    try: wt = gv.get_editor_property(prop); print("   widget_tree via", prop, "->", wt)
    except Exception as e: print("   no", prop, "->", str(e)[:100])
wt = None
try: wt = gv.get_editor_property("widget_tree")
except Exception: pass
if wt:
    root = wt.get_editor_property("root_widget"); print("   root:", root)
    found = []
    def walk(w):
        if w is None: return
        if w.get_name() == "ButtonBar" or isinstance(w, unreal.ButtonBarWidgetBase): found.append(w)
        if isinstance(w, unreal.PanelWidget):
            for i in range(w.get_children_count()): walk(w.get_child_at(i))
    walk(root); print("   ButtonBar widgets:", found)
    for b in found:
        data = b.get_editor_property("button_data"); print("   ButtonData:", [str(x.get_editor_property("button_label")) for x in data])
else:
    print("   fallback: WidgetBlueprintLibrary / EditorUtility?", [d for d in dir(unreal.WidgetBlueprint) if "tree" in d.lower() or "widget" in d.lower()][:20])
sec("done (read-only)")
