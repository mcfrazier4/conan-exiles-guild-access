"""READ-ONLY: roster widget classes (W_GuildMembers, W_ListEntry), text-block classes, RootWidget child plumbing docs."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def vars_of(path, only_own=True):
    bp = unreal.load_asset(path); sec(path)
    if not bp: print("   MISSING"); return
    print("   parent:", lib.get_blueprint_parent_class(bp).get_name())
    for v in lib.list_member_variable_names(bp):
        s = str(v)
        if only_own and s.startswith("/Script/"): continue
        try:
            t = lib.get_member_variable_type(bp, v); sub = t.get_editor_property("pin_sub_category_object")
            print(f"   {s:34} {t.get_editor_property('pin_category')} {sub.get_name() if sub else ''}")
        except Exception as e: print(f"   {s:34} ? {str(e)[:60]}")
for p in ("/Game/UI/Widgets/Guild/W_GuildMembers", "/Game/UI/Widgets/Guild/W_ListEntry", "/Game/UI/Widgets/Guild/W_ListMenu", "/Game/UI/Widgets/Buttons/WBP_ButtonCheckbox", "/Game/UI/Widgets/Buttons/WBP_ButtonBase"):
    vars_of(p)
sec("GuildViewBase own C++ props (types)")
for n in ("guild_members_list", "button_show_offline_members", "button_bar", "switcher_clan_settings"):
    try: print(f"   {n}: {getattr(unreal.GuildViewBase, n).__doc__.strip()[:120]}")
    except Exception as e: print(f"   {n}: ? {e}")
sec("RootWidget / WindowRoot plumbing docs")
for cls, fns in ((unreal.RootWidget, ("setup_new_child", "is_child_of_root", "key_nav_link_widget_array", "key_nav_link_panel_children", "set_window", "get_window")), (unreal.WindowRoot, ("get_root_widget_from_content_widget", "open_pop_up_window_bp"))):
    for fn in fns:
        f = getattr(cls, fn, None); print(f"   {cls.__name__}.{fn}: {(f.__doc__ or '').strip().replace(chr(10),' ')[:260] if f else 'MISSING'}")
sec("TextBlock subclasses")
tb = set(dir(unreal.TextBlock))
for cname in [c for c in dir(unreal) if c not in ("TextBlock",) and isinstance(getattr(unreal, c, None), type) and issubclass(getattr(unreal, c), unreal.TextBlock)]:
    print(f"   {cname}: {[d for d in dir(getattr(unreal, cname)) if not d.startswith('_') and d not in tb][:15]}")
print("   TextBlock has get_font:", hasattr(unreal.TextBlock, "get_font"), "set_font:", hasattr(unreal.TextBlock, "set_font"), "font prop:", "font" in dir(unreal.TextBlock))
sec("Widget assets under UI/Widgets/Text*, General")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/UI/Widgets", recursive=True):
    if re.search(r"Text|Label|Header|Row|Table|List", str(a.asset_name)) and "Guild" not in str(a.package_name): print("   ", a.package_name)
sec("done (read-only)")
