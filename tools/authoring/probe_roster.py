"""READ-ONLY: W_GuildView widget variables (names + classes), roster row widget, checkbox widget class, FLXButtonBase click plumbing."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def vars_of(path):
    bp = unreal.load_asset(path); sec(path)
    if not bp: print("   MISSING"); return
    print("   parent:", lib.get_blueprint_parent_class(bp))
    for v in lib.list_member_variable_names(bp):
        try: t = lib.get_member_variable_type(bp, v); print(f"   {str(v):34} {t}")
        except Exception as e: print(f"   {str(v):34} ? {str(e)[:60]}")
vars_of("/Game/UI/Widgets/Guild/W_GuildView")
for cand in ("/Game/UI/Widgets/Guild/W_GuildMemberEntry", "/Game/UI/Widgets/Guild/W_GuildMember", "/Game/UI/Widgets/Guild/W_GuildRosterEntry", "/Game/UI/Widgets/Guild/W_GuildViewMemberEntry"):
    if unreal.load_asset(cand): vars_of(cand)
sec("Guild widget assets on disk")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/UI/Widgets/Guild", recursive=True): print("   ", a.package_name)
sec("checkbox candidates")
for a in reg.get_assets_by_path("/Game/UI/Widgets", recursive=True):
    if re.search(r"Check|Toggle", str(a.asset_name)): print("   ", a.package_name)
sec("GuildViewBase C++ (members)")
base = set(dir(unreal.UserWidget)); print("  ", [d for d in dir(unreal.GuildViewBase) if not d.startswith("_") and d not in base])
sec("FLXButtonBase: dispatchers/functions")
print("  ", [d for d in dir(unreal.FLXButtonBase) if not d.startswith("_") and d not in base])
sec("W_GA_ClanRanks EventGraph: assign/bind nodes")
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
for n in ed.list_all_nodes():
    if re.search(r"Assign|Bind|Signal|Clicked|Toggled|Create|Add Child|AddChild", title(n)): print("   ", n.get_class().get_name(), title(n))
sec("done (read-only)")
