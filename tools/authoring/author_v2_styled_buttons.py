"""v2 - mod button subclasses whose class defaults carry a vanilla style. Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.
  W_GA_TabButton  : WBP_ButtonBase + FS_Button_Carousel, OnlyToggleOn   (the Roster/Ranks/Permissions tabs)
  W_GA_CellButton : WBP_ButtonBase + FS_Button_Clear                    (clickable rank-name cell, pencil icon)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
sec(f"mode = {MODE}")
wait_registry()
parent = unreal.load_class(None, "/Game/UI/Widgets/Buttons/WBP_ButtonBase.WBP_ButtonBase_C"); check(parent is not None, "WBP_ButtonBase_C")
for name, style_path, toggle in (("W_GA_TabButton", "/Game/UI/Styling/Buttons/FS_Button_Carousel", unreal.ToggleBehaviour.ONLY_TOGGLE_ON),
                                 ("W_GA_CellButton", "/Game/UI/Styling/Buttons/FS_Button_Clear", unreal.ToggleBehaviour.NEVER)):
    path = f"{LOCAL}/{name}"; disk = os.path.join(DISK_LOCAL, name + ".uasset")
    bp, created = load_or_create(path, parent); check(bp is not None, name); lib.compile_blueprint(bp)
    cls = unreal.load_class(None, f"{path}.{name}_C"); check(cls is not None, f"{name} class"); cdo = unreal.get_default_object(cls)
    style = unreal.load_class(None, f"{style_path}.{style_path.split('/')[-1]}_C"); check(style is not None, style_path)
    cdo.set_editor_property("style_asset_class", style); cdo.set_editor_property("toggle_behaviour", toggle)
    check(cdo.get_editor_property("style_asset_class") == style and cdo.get_editor_property("toggle_behaviour") == toggle, f"{name} defaults")
    lib.compile_blueprint(bp)
    if MODE == "real" and not failures: save(bp, disk, name)
result()
