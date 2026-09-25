"""v2 - 'Ranks' button on the Clan tab (W_GuildView override). Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

Event PreConstruct: if not RanksAdded -> ButtonBar.ButtonData += {ButtonLabel "Ranks"} -> RanksAdded = true (the bar builds its buttons from ButtonData afterwards)
On Button Index Clicked (ButtonBar) switch: pin 2 -> owning player's BPC_GA_Player.Server_ServerRequestClanTable
(the reply opens W_GA_ClanRanks on top of the clan window).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
GV_PATH = "/Game/UI/Widgets/Guild/W_GuildView"; GV_DISK = os.path.join(DISK_CONTENT, r"UI\Widgets\Guild\W_GuildView.uasset")
PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
sec(f"mode = {MODE}")
wait_registry()
gv = unreal.load_asset(GV_PATH); check(gv is not None, "loaded W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
if nodes_titled(ed, "MakeButtonBarData") or any("Ranks" in (PL.get_pin_value(p) or "") for n in ed.list_all_nodes() for p in lib.list_input_pins(n)):
    print("   exists")
else:
    if "RanksAdded" not in [str(v) for v in lib.list_member_variable_names(gv)]: check(lib.add_member_variable(gv, "RanksAdded", lib.get_basic_type_by_name("bool")), "var RanksAdded")
    lib.compile_blueprint(gv)
    # --- Construct: append the button
    cons = [n for n in ed.list_all_nodes() if title(n) == "Event Pre Construct"]
    if cons: ev = cons[0]
    else: ev = lib.add_event_override(gv, "PreConstruct", unreal.IntPoint(0, 0)); check(ev is not None, "Event PreConstruct")
    old = list(PL.list_connected_pins(then_out(ev)))
    seq = create_by_search(ed, [], ("FlowControl", "Sequence"), "Sequence", exact="Utilities|FlowControl|Sequence")
    PL.break_pin_links(then_out(ev)); connect(then_out(ev), exec_in(seq), "Construct -> Sequence")
    if old: connect(pin_exact_out(seq, "then_0"), old[0], "then_0 -> original")
    added = ed.add_get_member_variable_node("RanksAdded"); br = ed.add_branch_node(); connect(out(added), lib.find_condition_pin(br), "RanksAdded -> cond"); connect(pin_exact_out(seq, "then_1"), exec_in(br), "then_1 -> Branch")
    bar = ed.add_get_member_variable_node("ButtonBar"); check(bar is not None, "Get ButtonBar")
    data = ed.add_get_member_variable_node("ButtonData", "/Script/ConanSandbox.ButtonBarWidgetBase"); check(data is not None, "Get ButtonData (ButtonBar)"); connect(out(bar), selfpin(data), "ButtonBar -> Get ButtonData")
    mk = create_by_search(ed, [], ("Struct", "MakeButtonBarData"), "MakeButtonBarData", exact="Utilities|Struct|MakeButtonBarData"); print("   MakeButtonBarData pins:", pins(mk))
    lab = next((p for p in lib.list_input_pins(mk) if "Label" in str(PL.get_pin_name(p))), None); check(lab is not None, "ButtonLabel pin")
    PL.set_pin_value(lab, text_lit("RanksButton", "Ranks"))
    add = create_by_search(ed, [out(data)], ("Array", "Add"), "Array Add", exact="Utilities|Array|Add"); connect(out(data), pin_exact_in(add, "TargetArray"), "data -> Add"); connect(out(mk), pin_exact_in(add, "NewItem"), "struct -> Add")
    connect(lib.find_else_pin(br), exec_in(add), "not added -> Add")
    st = ed.add_set_member_variable_node("RanksAdded"); PL.set_pin_value(pin_exact_in(st, "RanksAdded"), "true"); connect(then_out(add), exec_in(st), "Add -> RanksAdded = true")
    # --- click: switch pin 2
    sw = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_SwitchInteger"]; check(len(sw) == 1, "Switch on Int"); sw = sw[0]
    before = [str(PL.get_pin_name(p)) for p in lib.list_output_pins(sw)]
    check(ed.add_node_pin(sw), "Switch: add pin"); newp = [p for p in lib.list_output_pins(sw) if str(PL.get_pin_name(p)) not in before]; check(len(newp) == 1, f"new switch pin {[str(PL.get_pin_name(p)) for p in newp]}")
    gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"])
    gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(out(gop, "ReturnValue"), pin_exact_in(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
    rpc = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "ServerRequestClanTable"); connect(out(gcb, "ReturnValue"), selfpin(rpc), "component -> rpc"); connect(newp[0], exec_in(rpc), "switch 2 -> rpc")
compile_ok(gv, [(ed, "EventGraph")], "W_GuildView")
if MODE == "real" and not failures: save(gv, GV_DISK, "W_GuildView override")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
