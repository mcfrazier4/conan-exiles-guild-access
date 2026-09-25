"""v2 - open the Clan Ranks panel IN PLACE of the clan roster. Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=player|guildview. Idempotent.

player   : BPC_GA_Player gets RanksHost (GuildViewBase). In the ClientClanTable handler, after CreateWidget:
           panel.Host = RanksHost; if RanksHost valid -> RanksHost.GuildMembersList.GetParent().AddChild(panel),
           roster + ShowOffline collapsed, RanksHost.SetupNewChild(panel), RanksHost = null;
           else -> the old AddToViewport path (fallback).
guildview: W_GuildView override: switch pin 2 -> component.RanksHost = self -> Server_ServerRequestClanTable (existing call).
Run 'player' first (guildview needs the RanksHost variable), and author_v2_widget3.py before both (Host variable on the panel).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "player").lower()
PL_PATH = f"{LOCAL}/BPC_GA_Player"; PL_C = f"{PL_PATH}.BPC_GA_Player_C"; W_C = f"{LOCAL}/W_GA_ClanRanks.W_GA_ClanRanks_C"
GV_PATH = "/Game/UI/Widgets/Guild/W_GuildView"; GV_DISK = os.path.join(DISK_CONTENT, r"UI\Widgets\Guild\W_GuildView.uasset")
GVB = "/Script/ConanSandbox.GuildViewBase"
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def set_vis(ed, widget_pin, vis, tail, label):
    v = call(ed, "/Script/UMG.Widget:SetVisibility", f"SetVisibility({label})"); connect(widget_pin, selfpin(v), label); setval(v, "InVisibility", vis); connect(tail, exec_in(v), f"-> {label} {vis}"); return then_out(v)
if TARGET == "player":
    pl = unreal.load_asset(PL_PATH); ed = GE.get_graph_editor_by_name(pl, "EventGraph")
    if "RanksHost" not in [str(v) for v in lib.list_member_variable_names(pl)]:
        check(lib.add_member_variable(pl, "RanksHost", lib.get_object_reference_type(unreal.GuildViewBase)), "var RanksHost"); lib.compile_blueprint(pl)
    if nodes_titled(ed, "SetupNewChild"): print("   exists")
    else:
        cw = [n for n in ed.list_all_nodes() if "CreateWidget" in n.get_class().get_name()]; check(len(cw) == 1, "the CreateWidget node"); cw = cw[0]
        panel = out(cw, "ReturnValue"); nxt = list(PL.list_connected_pins(then_out(cw))); check(len(nxt) == 1 and title(PL.get_owning_node(nxt[0])).replace(" ", "") == "AddToViewport", f"CreateWidget -> AddToViewport ({[title(PL.get_owning_node(p)) for p in nxt]})")
        atv_exec = nxt[0]; PL.break_pin_links(then_out(cw))
        host = ed.add_get_member_variable_node("RanksHost")
        sh = ed.add_set_member_variable_node("Host", W_C); check(sh is not None, "Set Host (panel)"); connect(panel, selfpin(sh), "panel"); connect(out(host), pin_exact_in(sh, "Host"), "RanksHost -> Host")
        connect(then_out(cw), exec_in(sh), "CreateWidget -> Set Host")
        iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", "IsValid(RanksHost)"); connect(out(host), pin_exact_in(iv, "Object"), "host")
        br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(then_out(sh), exec_in(br), "-> Branch")
        connect(lib.find_else_pin(br), atv_exec, "no host -> AddToViewport (fallback)")
        gl = ed.add_get_member_variable_node("GuildMembersList", GVB); connect(out(host), selfpin(gl), "host -> roster")
        gb = ed.add_get_member_variable_node("ButtonShowOfflineMembers", GVB); connect(out(host), selfpin(gb), "host -> show offline")
        gp = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(roster)"); connect(out(gl), selfpin(gp), "roster")
        ac = call(ed, "/Script/UMG.PanelWidget:AddChild", "AddChild(panel)"); connect(out(gp, "ReturnValue"), selfpin(ac), "parent"); connect(panel, pin_exact_in(ac, "Content"), "panel")
        connect(then_out(br), exec_in(ac), "valid -> AddChild"); t = then_out(ac)
        t = set_vis(ed, out(gl), "Collapsed", t, "roster"); t = set_vis(ed, out(gb), "Collapsed", t, "show offline")
        sn = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", "SetupNewChild(panel)"); connect(out(host), selfpin(sn), "host"); connect(panel, pin_exact_in(sn, "child"), "panel"); connect(t, exec_in(sn), "-> SetupNewChild"); t = then_out(sn)
        clr = ed.add_set_member_variable_node("RanksHost"); connect(t, exec_in(clr), "-> RanksHost = null")
    compile_ok(pl, [(ed, "EventGraph")], "BPC_GA_Player")
    if MODE == "real" and not failures: save(pl, os.path.join(DISK_LOCAL, "BPC_GA_Player.uasset"), "BPC_GA_Player")
    elif MODE == "real": print("   NOT SAVING: failures above")
else:
    gv = unreal.load_asset(GV_PATH); check(gv is not None, "loaded W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
    if nodes_titled(ed, "Set Ranks Host"): print("   exists")
    else:
        rpc = nodes_titled(ed, "Server Request Clan Table") or [n for n in ed.list_all_nodes() if "RequestClanTable" in title(n).replace(" ", "")]
        check(len(rpc) == 1, f"the RPC call node ({[title(n) for n in rpc]})"); rpc = rpc[0]
        comp_pin = list(PL.list_connected_pins(selfpin(rpc))); check(len(comp_pin) == 1, "component feeding the RPC"); comp_pin = comp_pin[0]
        feeder = list(PL.list_connected_pins(exec_in(rpc))); check(len(feeder) == 1, "switch pin feeding the RPC"); feeder = feeder[0]
        me = create_by_search(ed, [], ("Getareferencetoself",), "self", exact="Variables|Getareferencetoself")
        sh = ed.add_set_member_variable_node("RanksHost", PL_C); check(sh is not None, "Set RanksHost (component)"); connect(comp_pin, selfpin(sh), "component"); connect(out(me), pin_exact_in(sh, "RanksHost"), "self -> RanksHost")
        PL.break_pin_links(exec_in(rpc)); connect(feeder, exec_in(sh), "switch 2 -> Set RanksHost"); connect(then_out(sh), exec_in(rpc), "-> RPC")
    compile_ok(gv, [(ed, "EventGraph")], "W_GuildView")
    if MODE == "real" and not failures: save(gv, GV_DISK, "W_GuildView override")
    elif MODE == "real": print("   NOT SAVING: failures above")
result()
