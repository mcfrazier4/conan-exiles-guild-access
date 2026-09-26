"""v2 - remove the 'Ranks' ButtonData entry (index 2) from the W_GuildView override's ButtonBar, headlessly.
The widget tree is not exposed through the Blueprint API, but the ButtonBar instance is a UObject with a stable path
inside the package, so it is loaded directly. Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
GV_PATH = "/Game/UI/Widgets/Guild/W_GuildView"; GV_DISK = os.path.join(DISK_CONTENT, r"UI\Widgets\Guild\W_GuildView.uasset")
sec(f"mode = {MODE}")
wait_registry()
gv = unreal.load_asset(GV_PATH); check(gv is not None, "loaded W_GuildView")
bar = None
for path in (f"{GV_PATH}.W_GuildView:WidgetTree.ButtonBar", f"{GV_PATH}.W_GuildView:WidgetTree:ButtonBar"):
    bar = unreal.find_object(None, path) or unreal.load_object(None, path)
    if bar: print("   found ButtonBar via", path); break
if bar is None:
    # fall back: walk the package's objects
    for o in unreal.EditorAssetLibrary.load_asset(GV_PATH).get_outer().get_outermost().get_name() and []: pass
check(bar is not None, "ButtonBar widget instance")
if bar:
    data = list(bar.get_editor_property("button_data")); labels = [str(d.get_editor_property("button_label")) for d in data]; print("   ButtonData labels:", labels)
    keep = [d for d in data if "Ranks" not in str(d.get_editor_property("button_label"))]
    if len(keep) == len(data): print("   no Ranks entry; nothing to do")
    else:
        arr = unreal.Array(type(data[0]))
        for d in keep: arr.append(d)
        try: bar.set_editor_property("button_data", arr)
        except Exception as e: print("   set_editor_property failed:", str(e)[:200]); check(False, "write ButtonData")
        try: bar.modify()
        except Exception: pass
        print("   ButtonData now:", [str(d.get_editor_property("button_label")) for d in bar.get_editor_property("button_data")])
        lib.compile_blueprint(gv)
        if MODE == "real": save(gv, GV_DISK, "W_GuildView override")
    print("   C++ ButtonBarWidgetBase members:", [d for d in dir(unreal.ButtonBarWidgetBase) if "button" in d.lower()])
result()
