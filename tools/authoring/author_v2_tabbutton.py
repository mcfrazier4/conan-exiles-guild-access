"""v2 - W_GA_TabButton: a child of the vanilla WBP_ButtonBase whose class defaults carry the top-nav look
(StyleAssetClass = FS_Button_Carousel, ToggleBehaviour = OnlyToggleOn). Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
PATH = f"{LOCAL}/W_GA_TabButton"; DISK = os.path.join(DISK_LOCAL, "W_GA_TabButton.uasset")
sec(f"mode = {MODE}")
wait_registry()
parent = unreal.load_class(None, "/Game/UI/Widgets/Buttons/WBP_ButtonBase.WBP_ButtonBase_C"); check(parent is not None, "WBP_ButtonBase_C")
tab, created = load_or_create(PATH, parent); check(tab is not None, "W_GA_TabButton")
lib.compile_blueprint(tab)
cls = unreal.load_class(None, f"{PATH}.W_GA_TabButton_C"); check(cls is not None, "generated class"); cdo = unreal.get_default_object(cls)
style = unreal.load_class(None, "/Game/UI/Styling/Buttons/FS_Button_Carousel.FS_Button_Carousel_C"); check(style is not None, "FS_Button_Carousel_C")
cdo.set_editor_property("style_asset_class", style); cdo.set_editor_property("toggle_behaviour", unreal.ToggleBehaviour.ONLY_TOGGLE_ON)
check(cdo.get_editor_property("style_asset_class") == style, "defaults: style = Carousel"); check(cdo.get_editor_property("toggle_behaviour") == unreal.ToggleBehaviour.ONLY_TOGGLE_ON, "defaults: toggle = OnlyToggleOn")
lib.compile_blueprint(tab)
if MODE == "real" and not failures: save(tab, DISK, "W_GA_TabButton")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
