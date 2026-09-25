"""A8 - radial rank badges at 50% size, centred. Imports 92x92 PNGs (tools/authoring/icons_src/out, built from the
vanilla 16x23 T_Rank_* badges) as UI textures under the mod namespace and repoints the four AddSubItem icon pins on
each leaf override. Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=container|door|builddoor|import. Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "import").lower()
RANKS = ["Recruit", "Member", "Officer", "GuildMaster"]; LABELS = ["Recruit", "Member", "Officer", "Guild Master"]
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons_src", "out")
CLASSES = {"container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
           "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset"),
           "builddoor": ("/Game/Systems/Building/BP_BuildDoor", r"Systems\Building\BP_BuildDoor.uasset")}
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
if TARGET == "import":
    for r in RANKS:
        name = f"T_GA_Rank_{r}"; disk = os.path.join(DISK_LOCAL, name + ".uasset"); png = os.path.join(SRC, name + ".png")
        check(os.path.exists(png), f"source {png}")
        if unreal.load_asset(f"{LOCAL}/{name}") is not None and os.path.exists(disk): print(f"   {name}: already imported"); continue
        if MODE != "real": print(f"   {name}: would import -> {LOCAL}/{name}"); continue
        task = unreal.AssetImportTask(); task.set_editor_property("filename", png); task.set_editor_property("destination_path", LOCAL)
        task.set_editor_property("destination_name", name); task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        tex = unreal.load_asset(f"{LOCAL}/{name}"); check(tex is not None, f"{name} imported")
        if tex:
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)   # UserInterface2D: no DXT blockiness
            tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TEXTUREGROUP_UI if hasattr(unreal.TextureMipGenSettings, "TEXTUREGROUP_UI") else unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI); tex.set_editor_property("srgb", True); tex.set_editor_property("never_stream", True)
            print(f"   {name}: {tex.blueprint_get_size_x()}x{tex.blueprint_get_size_y()}")
            save(tex, disk, name)
else:
    PATH, REL = CLASSES[TARGET]
    for r in RANKS: check(unreal.load_asset(f"{LOCAL}/T_GA_Rank_{r}") is not None, f"texture T_GA_Rank_{r} (run GA_TARGET=import first)")
    bp = unreal.load_asset(PATH); check(bp is not None, f"loaded {PATH}"); ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    subs = nodes_titled(ed, "AddSubItem"); check(len(subs) == 4, f"four AddSubItem nodes ({len(subs)})")
    changed = 0
    for n in subs:
        label = PL.get_pin_value(lib.find_input_pin(n, "label")) or ""
        idx = next((i for i, l in enumerate(LABELS) if f'"{l}"' in label), None)
        if idx is None: check(False, f"unrecognised sub-item label {label[:60]!r}"); continue
        icon = f"{LOCAL}/T_GA_Rank_{RANKS[idx]}.T_GA_Rank_{RANKS[idx]}"
        if PL.get_pin_value(lib.find_input_pin(n, "icon")) == icon: print(f"   {LABELS[idx]}: already T_GA_Rank_{RANKS[idx]}"); continue
        setval(n, "icon", icon, f"{LABELS[idx]} icon -> T_GA_Rank_{RANKS[idx]}"); changed += 1
    compile_ok(bp, [(ed, "EventGraph")], TARGET)
    if MODE == "real" and not failures and changed: save(bp, os.path.join(DISK_CONTENT, REL), TARGET)
    elif MODE == "real" and failures: print("   NOT SAVING: failures above")
result()
