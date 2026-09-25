"""Export the rank badges to PNG (scratch) and report the vanilla radial icon size. Writes only PNGs to the scratch folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
OUT = r"E:\ClaudeCode\conan-exiles\guild-access\tools\authoring\icons_src"; os.makedirs(OUT, exist_ok=True)
wait_registry()
for p in ("/Game/UI/Textures/GUIs/MainRadialMenu/MainRadialMenuIconLocked", "/Game/UI/Textures/GUIs/MainRadialMenu/T_MainRadialMenuIconOpen"):
    t = unreal.load_asset(p); print(f"   {p.split('/')[-1]}: {t.blueprint_get_size_x()}x{t.blueprint_get_size_y()}" if t else f"   {p}: MISSING")
for r in ("Recruit", "Member", "Officer", "GuildMaster"):
    t = unreal.load_asset(f"/Game/UI/Textures/GUIs/Guild/T_Rank_{r}")
    task = unreal.AssetExportTask(); task.set_editor_property("object", t); task.set_editor_property("filename", os.path.join(OUT, f"T_Rank_{r}.png"))
    task.set_editor_property("exporter", unreal.TextureExporterPNG()); task.set_editor_property("automated", True); task.set_editor_property("replace_identical", True); task.set_editor_property("prompt", False)
    ok = unreal.Exporter.run_asset_export_task(task); print(f"   export T_Rank_{r}: {ok} -> exists {os.path.exists(os.path.join(OUT, f'T_Rank_{r}.png'))}")
sec("done")
