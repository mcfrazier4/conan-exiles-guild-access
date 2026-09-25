"""READ-ONLY: GeneralText style API, text style assets, GuildMembersBase / ListEntryBase members."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
sec("GeneralText docs")
for fn in ("text_style_asset_class", "set_text_style", "max_character_count"):
    f = getattr(unreal.GeneralText, fn, None); print(f"   {fn}: {(f.__doc__ or '').strip().replace(chr(10),' ')[:300] if f else 'MISSING'}")
sec("style-ish C++ classes")
base = set(dir(unreal.Object))
for cname in [c for c in dir(unreal) if re.search(r"TextStyle|StyleAsset|FLXStyle|ButtonStyle", c)]:
    c = getattr(unreal, cname); print(f"   {cname} (parent {c.__mro__[1].__name__}): {[d for d in dir(c) if not d.startswith('_') and d not in base][:20]}")
sec("style assets in the registry")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
hits = [a for a in reg.get_assets_by_path("/Game/UI", recursive=True) if re.search(r"Style|FS_", str(a.package_name))]
print("   count:", len(hits))
for a in hits[:80]: print("   ", a.package_name, "|", a.asset_class_path.asset_name if hasattr(a, "asset_class_path") else a.asset_class)
sec("GuildMembersBase / ListEntryBase / ListMenu members")
uw = set(dir(unreal.UserWidget))
for cls in (unreal.GuildMembersBase, unreal.ListEntryBase, unreal.ListMenu):
    print(f"   {cls.__name__}: {[d for d in dir(cls) if not d.startswith('_') and d not in uw]}")
sec("W_ListEntry / W_GuildMembers: EventGraph node titles mentioning text/style")
for p in ("/Game/UI/Widgets/Guild/W_ListEntry", "/Game/UI/Widgets/Guild/W_GuildMembers"):
    bp = unreal.load_asset(p)
    for g in lib.list_graph_names(bp):
        ed = GE.get_graph_editor_by_name(bp, str(g))
        if not ed: continue
        ts = sorted(set(title(n) for n in ed.list_all_nodes() if re.search(r"Text|Style|Font|Entry|Rank", title(n))))
        if ts: print(f"   {p.split('/')[-1]}::{g}: {ts[:25]}")
sec("done (read-only)")
