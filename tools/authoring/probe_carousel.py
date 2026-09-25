"""READ-ONLY-ish: carousel C++ API, tab style defaults, runtime setters on FLXButtonBase, and whether a mod subclass of
WBP_ButtonBase can carry the Carousel style in its class defaults (created in memory; not saved in dry mode)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
uw = set(dir(unreal.UserWidget))
sec("carousel classes")
for cname in [c for c in dir(unreal) if re.search(r"Carousel", c) and isinstance(getattr(unreal, c, None), type)]:
    c = getattr(unreal, cname); print(f"   {cname} (parent {c.__mro__[1].__name__}): {[d for d in dir(c) if not d.startswith('_') and d not in uw][:40]}")
sec("style defaults")
for p in ("/Game/UI/Styling/Buttons/FS_Button_Carousel", "/Game/UI/Styling/Buttons/FS_Button_SecondaryTab"):
    cls = unreal.load_class(None, p + "." + p.split("/")[-1] + "_C"); cdo = cls.get_default_object()
    for k in ("material_background", "material_frame", "font_color_default"):
        try: print("  ", p.split("/")[-1], k, str(cdo.get_editor_property(k))[:80])
        except Exception as e: print("  ", p.split("/")[-1], k, "?", str(e)[:60])
sec("runtime setters on an FLXButtonBase pin")
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
lib.add_member_variable(w, "ZZ_Btn", lib.get_object_reference_type(unreal.FLXButtonBase)); lib.compile_blueprint(w)
g = ed.add_get_member_variable_node("ZZ_Btn"); bp_ = lib.list_output_pins(g)[0]
print("   btn actions:", [a for a in available(ed, [bp_]) if re.search(r"StyleAsset|ToggleBehav|SetIsToggledOn|SetLabel|SignalToggled|SignalClicked", a)][:12])
ed.remove_nodes([g]); ed.remove_member_variable("ZZ_Btn")
sec("child class W_GA_TabButton with Carousel style in its defaults")
parent = unreal.load_class(None, "/Game/UI/Widgets/Buttons/WBP_ButtonBase.WBP_ButtonBase_C")
tab, _created = load_or_create(f"{LOCAL}/W_GA_TabButton", parent); print("   W_GA_TabButton:", tab, "parent:", lib.get_blueprint_parent_class(tab).get_name() if tab else None)
if tab:
    lib.compile_blueprint(tab); cls = unreal.load_class(None, f"{LOCAL}/W_GA_TabButton.W_GA_TabButton_C"); cdo = unreal.get_default_object(cls) if cls else None
    print("   cdo:", cdo)
    try:
        style = unreal.load_class(None, "/Game/UI/Styling/Buttons/FS_Button_Carousel.FS_Button_Carousel_C"); cdo.set_editor_property("style_asset_class", style); print("   style set ->", cdo.get_editor_property("style_asset_class"))
    except Exception as e: print("   CDO style set failed:", str(e)[:200])
    en = getattr(unreal, "ToggleBehaviour", None) or getattr(unreal, "EToggleBehaviour", None); print("   toggle enum:", en, [d for d in dir(en) if d.isupper()] if en else None)
    try: cdo.set_editor_property("toggle_behaviour", en.ONLY_TOGGLE_ON); print("   toggle set ->", cdo.get_editor_property("toggle_behaviour"))
    except Exception as e: print("   CDO toggle set failed:", str(e)[:200])
    if MODE == "real": lib.compile_blueprint(tab); save(tab, os.path.join(DISK_LOCAL, "W_GA_TabButton.uasset"), "W_GA_TabButton")
sec("done")
sec("roster text styles (W_GuildMembers / W_ListEntry exports)")
OUT = r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad"
for p in ("/Game/UI/Widgets/Guild/W_GuildMembers", "/Game/UI/Widgets/Guild/W_ListEntry"):
    a = unreal.load_asset(p); fn = os.path.join(OUT, p.split("/")[-1] + ".t3d")
    task = unreal.AssetExportTask(); task.set_editor_property("object", a); task.set_editor_property("filename", fn); task.set_editor_property("automated", True); task.set_editor_property("replace_identical", True); task.set_editor_property("prompt", False); task.set_editor_property("exporter", unreal.ObjectExporterT3D())
    print("   export", p.split("/")[-1], unreal.Exporter.run_asset_export_task(task))
sec("done 2")
