"""READ-ONLY: W_GuildView widget tree (via T3D export to the scratch dir), tab-bar widget classes, top-nav tab widget."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
OUT = r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad"; os.makedirs(OUT, exist_ok=True)
wait_registry()
sec("T3D export of W_GuildView (override) and W_GA_ClanRanks")
for p in ("/Game/UI/Widgets/Guild/W_GuildView", f"{LOCAL}/W_GA_ClanRanks"):
    a = unreal.load_asset(p); fn = os.path.join(OUT, p.split("/")[-1] + ".t3d")
    task = unreal.AssetExportTask(); task.set_editor_property("object", a); task.set_editor_property("filename", fn); task.set_editor_property("automated", True); task.set_editor_property("replace_identical", True); task.set_editor_property("prompt", False)
    try: task.set_editor_property("exporter", unreal.ObjectExporterT3D())
    except Exception as e: print("   exporter:", e)
    ok = unreal.Exporter.run_asset_export_task(task); print(f"   {p}: {ok} -> {fn} {os.path.getsize(fn) if os.path.exists(fn) else 'missing'} B")
sec("tab-ish widget assets")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for a in reg.get_assets_by_path("/Game/UI", recursive=True):
    if re.search(r"Tab", str(a.asset_name)): print("   ", a.package_name)
sec("tab-ish C++ classes")
base = set(dir(unreal.UserWidget))
for cname in [c for c in dir(unreal) if re.search(r"Tab", c) and isinstance(getattr(unreal, c, None), type)]:
    c = getattr(unreal, cname)
    if issubclass(c, unreal.Widget): print(f"   {cname} (parent {c.__mro__[1].__name__}): {[d for d in dir(c) if not d.startswith('_') and d not in base][:25]}")
sec("done (read-only)")
