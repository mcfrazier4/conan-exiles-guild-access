"""READ-ONLY: the vanilla checkbox/button widget API and the styled text block class."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
base = set(dir(unreal.UserWidget))
sec("FLXButtonBase (WBP_ButtonBase / WBP_ButtonCheckbox parent): non-UserWidget members")
print("  ", [d for d in dir(unreal.FLXButtonBase) if not d.startswith("_") and d not in base])
for fn in ("set_is_toggled_on", "get_is_toggled_on", "set_label", "set_button_label", "signal_clicked", "on_clicked", "set_toggle_behaviour", "set_is_checked"):
    f = getattr(unreal.FLXButtonBase, fn, None)
    if f: print(f"   --- {fn}: {(f.__doc__ or '').strip().replace(chr(10), ' ')[:200]}")
sec("text block classes with a text style asset")
tb = set(dir(unreal.TextBlock))
for cname in [c for c in dir(unreal) if re.search(r"TextBlock|RichText", c)]:
    c = getattr(unreal, cname)
    extra = [d for d in dir(c) if not d.startswith("_") and d not in tb]
    if extra: print(f"   {cname}: {extra[:20]}")
sec("ButtonBarWidgetBase: button_data / delegates")
bb = set(dir(unreal.UserWidget))
print("  ", [d for d in dir(unreal.ButtonBarWidgetBase) if not d.startswith("_") and d not in bb])
sec("styled asset classes")
for p in ("/Game/UI/Styling/Texts/FS_Text_Body", "/Game/UI/Styling/Texts/FS_Text_Heading", "/Game/UI/Styling/Buttons/FS_Button_Checkbox_Clan", "/Game/UI/Styling/Buttons/FS_Button_Default", "/Game/UI/Textures/GUIs/Guild/T_BgPanel"):
    a = unreal.load_asset(p); print(f"   {p}: {a.get_class().get_name() if a else 'MISSING'}")
sec("W_GA_ClanRanks: available widget-construction node for WBP_ButtonCheckbox / actions on a FLXButtonBase pin")
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
lib.add_member_variable(w, "ZZ_Tmp", lib.get_object_reference_type(unreal.FLXButtonBase)); lib.compile_blueprint(w)
g = ed.add_get_member_variable_node("ZZ_Tmp"); pin = lib.list_output_pins(g)[0]
print("   actions on FLXButtonBase pin (Assign/Toggle/Label):", [a for a in available(ed, [pin]) if re.search(r"Assign|Toggle|Label|Checked|Clicked", a)][:20])
ed.remove_nodes([g]); ed.remove_member_variable("ZZ_Tmp")
sec("done (read-only; temp var removed, not saved)")
