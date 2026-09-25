"""READ-ONLY: the game's clan/guild permission model (enums, Guild API, rank-related functions)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
base = set(dir(unreal.Object))
sec("enums mentioning Guild/Clan/Rank/Permission")
for cname in [c for c in dir(unreal) if re.search(r"Guild|Clan|Rank|Permission", c) and isinstance(getattr(unreal, c, None), type) and issubclass(getattr(unreal, c), unreal.EnumBase)]:
    print(f"   {cname}: {[d for d in dir(getattr(unreal, cname)) if d.isupper()]}")
sec("Guild class: rank/permission-ish members")
print("  ", [d for d in dir(unreal.Guild) if not d.startswith("_") and d not in base and re.search(r"rank|perm|officer|master|can_|allow|promote|invite|kick|motd|name|treasur|coffer|leader", d)])
for fn in [d for d in dir(unreal.Guild) if re.search(r"^(can_|is_|get_player_rank|get_rank|set_rank|has_)", d)]:
    f = getattr(unreal.Guild, fn); print(f"   {fn}: {(f.__doc__ or '').strip().replace(chr(10),' ')[:160]}")
sec("other classes with 'Guild' in the name (C++)")
for cname in [c for c in dir(unreal) if re.search(r"Guild", c) and isinstance(getattr(unreal, c, None), type) and not issubclass(getattr(unreal, c), unreal.EnumBase)][:30]:
    c = getattr(unreal, cname); print(f"   {cname}: {[d for d in dir(c) if not d.startswith('_') and d not in base and re.search(r'rank|perm|officer|can_', d)][:15]}")
sec("Leave-guild popup / modal classes")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/UI/Widgets/Modals", recursive=True): print("   ", a.package_name)
sec("done (read-only)")
