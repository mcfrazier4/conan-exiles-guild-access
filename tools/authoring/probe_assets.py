"""READ-ONLY: row highlight brush, checkmark / pencil textures, W_RenameInput + W_MessageBox API, ModController GetRankName signature."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
reg = unreal.AssetRegistryHelpers.get_asset_registry()
sec("textures: check / pencil / edit / highlight")
for a in reg.get_assets_by_path("/Game/UI/Textures", recursive=True):
    if re.search(r"Check|Pencil|Edit|Tick|Highlight|RowBG|ListEntry|Row", str(a.asset_name), re.I): print("   ", a.package_name)
sec("W_ListEntry Highlight brush")
t = open(r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad\W_ListEntry.t3d", encoding="utf-8", errors="replace").read()
m = re.search(r'Begin Object Name="Highlight"(.*?)End Object', t, re.S); print("   ", [l.strip()[:300] for l in m.group(1).splitlines() if re.search(r"Brush|Color|Visib", l)])
m = re.search(r'Begin Object Name="Border_0"(.*?)End Object', t, re.S); print("   Border_0:", [l.strip()[:200] for l in m.group(1).splitlines() if re.search(r"Brush|Color|Padding", l)])
m = re.search(r'Begin Object Name="Rank"(.*?)End Object', t, re.S); print("   Rank img:", [l.strip()[:300] for l in m.group(1).splitlines() if re.search(r"Brush|Color", l)])
m = re.search(r'Begin Object Name="ButtonEditClanName"(.*?)End Object', open(r"C:\Users\micha\AppData\Local\Temp\claude\E--ClaudeCode-conan-exiles-guild-access\9433ee40-3a5e-4e7e-826e-bd349c520de6\scratchpad\W_GuildView.t3d", encoding="utf-8", errors="replace").read(), re.S)
print("   ButtonEditClanName (pencil):", [l.strip()[:200] for l in m.group(1).splitlines() if re.search(r"Icon|Style|Label", l)])
sec("modal widgets")
uw = set(dir(unreal.UserWidget))
for p in ("/Game/UI/Widgets/Modals/W_RenameInput", "/Game/UI/Widgets/Modals/W_MessageBox"):
    bp = unreal.load_asset(p); par = lib.get_blueprint_parent_class(bp); print("  ", p.split("/")[-1], "parent:", par.get_name(), "graphs:", [str(g) for g in lib.list_graph_names(bp)], "dispatchers:", [str(d) for d in lib.list_event_dispatchers(bp)])
    print("     own vars:", [str(v) for v in lib.list_member_variable_names(bp) if not str(v).startswith("/Script/")])
    cname = par.get_name(); c = getattr(unreal, cname, None)
    if c: print("     C++:", [d for d in dir(c) if not d.startswith("_") and d not in uw and not d.startswith("key_nav")][:40])
sec("how W_GuildView opens the leave popup / rename")
gv = unreal.load_asset("/Game/UI/Widgets/Guild/W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
for n in ed.list_all_nodes():
    if re.search(r"PopUp|Popup|Rename|MessageBox|CreateDelegate|Leave", title(n)): print("   ", n.get_class().get_name(), title(n), pins(n)[:10])
sec("BPL / ModController rank name functions")
for p, fns in ((f"{LOCAL}/BPL_GuildAccess", None), (f"{LOCAL}/BP_GA_ModController", None)):
    bp = unreal.load_asset(p); print("  ", p.split("/")[-1], [str(g) for g in lib.list_graph_names(bp)])
sec("done (read-only)")
