"""v2 stage 2 - client/server plumbing on BPC_GA_Player and table builders on the ModController.
Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

BP_GA_ModController (+):
  BuildAllowed(GuildId) -> Array<Bool>   32 entries, index = perm*4 + rank
  BuildNames(GuildId)   -> Array<String> 4 entries

BPC_GA_Player (+):
  vars  CachedNames: Array<String>, CachedAllowed: Array<Bool>, CachedMyRank: Byte, CachedGuildId: Int, TableReady: Bool
  ServerRequestClanTable_0()                        (GUI: Run on Server, Reliable)
      -> owner pawn -> rank, guild -> BuildNames/BuildAllowed -> ClientClanTable
  ClientClanTable_0(Names, Allowed, MyRank, GuildId) (GUI: Run on owning Client, Reliable)
      -> stores the cache, TableReady = true
  ServerSetRankName_0(Rank, Name)                  (GUI: Run on Server, Reliable)  guild master only
  ServerSetTable_0(Allowed: Array<Bool>)           (GUI: Run on Server, Reliable)  guild master only
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
MOD_PATH = f"{LOCAL}/BP_GA_ModController"; MOD_C = f"{MOD_PATH}.BP_GA_ModController_C"
PL_PATH = f"{LOCAL}/BPC_GA_Player"; PL_C = f"{PL_PATH}.BPC_GA_Player_C"
byte_t, bool_t, int_t, str_t = [lib.get_basic_type_by_name(x) for x in ("byte", "bool", "int", "string")]
arr_bool, arr_str = lib.get_array_type(bool_t), lib.get_array_type(str_t)
M = "/Script/Engine.KismetMathLibrary:"
FORLOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"

sec(f"mode = {MODE}")
wait_registry()
mod = unreal.load_asset(MOD_PATH); pl = unreal.load_asset(PL_PATH); check(mod is not None and pl is not None, "loaded ModController + player component")

def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin_in(n, *names):
    for nm in names:
        p = lib.find_input_pin(n, nm)
        if p is not None: return p
    return None
def pin_out(n, *names):
    for nm in names:
        p = lib.find_output_pin(n, nm)
        if p is not None: return p
    return None
def forloop(ed, first, last):
    n = None
    try: n = ed.add_macro_node(FORLOOP)
    except Exception as e: print("   add_macro_node raised", type(e).__name__)
    if n is None: n = create_by_search(ed, [], ("FlowControl", "ForLoop"), "ForLoop", exact="Utilities|FlowControl|ForLoop")
    check(n is not None, "ForLoop macro")
    check(PL.set_pin_value(pin_exact_in(n, "FirstIndex"), str(first)), "ForLoop.FirstIndex"); check(PL.set_pin_value(pin_exact_in(n, "LastIndex"), str(last)), "ForLoop.LastIndex")
    return n
def array_add(ed, arr_pin, item_pin, label):
    a = create_by_search(ed, [arr_pin], ("Array", "Add"), f"Array Add ({label})", exact="Utilities|Array|Add")
    connect(arr_pin, pin_exact_in(a, "TargetArray"), f"{label}: array -> Add"); connect(item_pin, pin_exact_in(a, "NewItem"), f"{label}: item -> Add"); return a
def array_get(ed, arr_pin, idx_pin, label):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), f"Array Get ({label})", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), f"{label}: array -> Get"); connect(idx_pin, pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index"), f"{label}: index -> Get"); return out(g)
def int_div(ed, i_pin, d): n = call(ed, M + "Divide_IntInt", "int /"); connect(i_pin, pin_in(n, "A"), "i"); setval(n, "B", str(d)); return out(n, "ReturnValue")
def int_mod(ed, i_pin, d): n = call(ed, M + "Percent_IntInt", "int %"); connect(i_pin, pin_in(n, "A"), "i"); setval(n, "B", str(d)); return out(n, "ReturnValue")
def to_byte(ed, i_pin): n = call(ed, M + "Conv_IntToByte", "int->byte"); connect(i_pin, pin_in(n, "InInt"), "i"); return out(n, "ReturnValue")
def fn_graph(bp, name, inputs, outputs):
    if name in [str(x) for x in lib.list_graph_names(bp)]: return GE.get_graph_editor_by_name(bp, name), None, None, False
    g = lib.add_function_graph(bp, name); ed = GE.get_graph_editor(g)
    ins = {n: ed.add_graph_input_parameter(n, t, "") for n, t in inputs}
    ret = None
    for n, t in outputs: ret = ed.add_graph_output_parameter(n, t)
    return ed, ins, ret, True

# ============================================================= ModController builders
sec("ModController: BuildAllowed / BuildNames")
ed, ins, ret, new = fn_graph(mod, "BuildAllowed", [("GuildId", str_t)], [("Allowed", arr_bool)])
if new:
    check(ed.add_local_variable("Acc", arr_bool), "local Acc: Array<Bool>")
    acc = ed.add_get_local_variable_node("Acc"); check(acc is not None, "Get Acc")
    lp = forloop(ed, 0, 31); connect(ed.find_graph_entry_pin(), pin_exact_in(lp, "execute"), "entry -> ForLoop")
    idx = pin_exact_out(lp, "Index")
    isa = call(ed, f"{MOD_C}:IsAllowed", "IsAllowed"); connect(ins["GuildId"], pin_in(isa, "GuildId"), "g")
    connect(to_byte(ed, int_div(ed, idx, 4)), pin_in(isa, "Perm"), "perm"); connect(to_byte(ed, int_mod(ed, idx, 4)), pin_in(isa, "Rank"), "rank")
    connect(pin_exact_out(lp, "LoopBody"), exec_in(isa), "body -> IsAllowed")
    add = array_add(ed, out(acc), out(isa, "Allowed"), "allowed"); connect(then_out(isa), exec_in(add), "IsAllowed -> Add")
    connect(pin_exact_out(lp, "Completed"), exec_in(ret), "Completed -> Return")
    acc2 = ed.add_get_local_variable_node("Acc"); connect(out(acc2), pin_in(ret, "Allowed"), "Acc -> Return")
ed, ins, ret, new = fn_graph(mod, "BuildNames", [("GuildId", str_t)], [("Names", arr_str)])
if new:
    check(ed.add_local_variable("Acc", arr_str), "local Acc: Array<String>")
    acc = ed.add_get_local_variable_node("Acc")
    lp = forloop(ed, 0, 3); connect(ed.find_graph_entry_pin(), pin_exact_in(lp, "execute"), "entry -> ForLoop")
    grn = call(ed, f"{MOD_C}:GetRankName", "GetRankName"); connect(ins["GuildId"], pin_in(grn, "GuildId"), "g"); connect(to_byte(ed, pin_exact_out(lp, "Index")), pin_in(grn, "Rank"), "rank")
    connect(pin_exact_out(lp, "LoopBody"), exec_in(grn), "body -> GetRankName")
    add = array_add(ed, out(acc), out(grn, "Name"), "name"); connect(then_out(grn), exec_in(add), "-> Add")
    connect(pin_exact_out(lp, "Completed"), exec_in(ret), "Completed -> Return"); acc2 = ed.add_get_local_variable_node("Acc"); connect(out(acc2), pin_in(ret, "Names"), "Acc -> Return")
compile_ok(mod, [(GE.get_graph_editor_by_name(mod, g), g) for g in ("BuildAllowed", "BuildNames")], "BP_GA_ModController")

# ============================================================= player component
sec("player component: cache variables")
have = [str(v) for v in lib.list_member_variable_names(pl)]
for nm, t in (("CachedNames", arr_str), ("CachedAllowed", arr_bool), ("CachedMyRank", byte_t), ("CachedGuildId", str_t), ("TableReady", bool_t)):
    if nm not in have: check(lib.add_member_variable(pl, nm, t), f"var {nm}")
sec("player component: event signatures (dispatcher trick)")
disp = [str(x) for x in lib.list_event_dispatchers(pl)]
def sig(name, params):
    if name in disp: return
    check(lib.add_event_dispatcher(pl, name), f"signature {name}")
    for pn, pt in params: check(lib.add_event_dispatcher_parameter(pl, name, pn, pt), f"  param {pn}")
sig("ClientClanTable", [("Names", arr_str), ("Allowed", arr_bool), ("MyRank", byte_t), ("GuildId", str_t)])
sig("ServerSetRankName", [("Rank", byte_t), ("Name", str_t)])
sig("ServerSetTable", [("Allowed", arr_bool)])
check(lib.compile_blueprint(pl), "compile (skeleton)")
ped = GE.get_graph_editor_by_name(pl, "EventGraph")
def event_node(name):
    hits = [n for n in ped.list_all_nodes() if n.get_class().get_name() == "K2Node_CustomEvent" and title(n).replace("Server_", "").replace("Client_", "").startswith(name)]
    if hits: print(f"   event {title(hits[0])!r} exists"); return hits[0], False
    n = ped.add_dispatcher_event_node(name) if name in [str(x) for x in lib.list_event_dispatchers(pl)] else ped.add_custom_event_node(name)
    check(n is not None, f"event {name} -> {title(n) if n else None} {pins(n) if n else ''}"); return n, True
def owner_pawn_rank(ed, tail):
    """owner controller -> pawn -> GetPawnRank; returns (tail, pawn_pin, rank_pin, controller_pin)"""
    own = call(ed, "/Script/Engine.ActorComponent:GetOwner", "GetOwner")
    cast = create_by_search(ed, [out(own, "ReturnValue")], ("Cast", "Controller"), "Cast To Controller", exact="Utilities|Casting|CastToController")
    connect(out(own, "ReturnValue"), pin_in(cast, "Object"), "owner -> cast"); connect(tail, exec_in(cast), "-> CastToController")
    gp = call(ed, "/Script/Engine.Controller:K2_GetPawn", "GetPawn"); connect(as_pin(cast), lib.find_self_pin(gp) or pin_in(gp, "self"), "controller -> GetPawn")
    gpr = call(ed, f"{BPL_C}:GetPawnRank", "GetPawnRank"); connect(out(gp, "ReturnValue"), pin_in(gpr, "Pawn"), "pawn -> GetPawnRank"); connect(then_out(cast), exec_in(gpr), "cast -> GetPawnRank")
    return then_out(gpr), out(gp, "ReturnValue"), out(gpr, "Rank"), as_pin(cast)
def guild_id(ed, pawn_pin, tail):
    """pawn -> ConanCharacter -> GetGuildStableId -> string; returns (tail, string pin)"""
    cc = create_by_search(ed, [pawn_pin], ("Cast", "ConanCharacter"), "Cast To ConanCharacter", exact="Utilities|Casting|CastToConanCharacter")
    connect(pawn_pin, pin_in(cc, "Object"), "pawn -> cast"); connect(tail, exec_in(cc), "-> CastToConanCharacter")
    gid = call(ed, "/Script/ConanSandbox.ConanCharacter:GetGuildStableId", "GetGuildStableId"); connect(as_pin(cc), lib.find_self_pin(gid) or pin_in(gid, "self"), "char -> GetGuildStableId")
    t = then_out(cc)
    if has_exec(gid): connect(t, exec_in(gid), "cast -> GetGuildStableId"); t = then_out(gid)
    conv = call(ed, unreal.StableIdFunctionLibrary.static_class().get_path_name() + ":Conv_StableIdToString", "StableId->String"); connect(out(gid, "ReturnValue"), lib.list_input_pins(conv)[0], "stable id -> string")
    if has_exec(conv): connect(t, exec_in(conv), "-> Conv"); t = then_out(conv)
    return t, out(conv, "ReturnValue")

sec("ServerRequestClanTable")
ev, new = event_node("ServerRequestClanTable")
if new:
    tail, pawn, rank, ctl = owner_pawn_rank(ped, then_out(ev))
    tail, gid = guild_id(ped, pawn, tail)
    gc = call(ped, f"{BPL_C}:GetGAController", "GetGAController"); connect(tail, exec_in(gc), "-> GetGAController"); ctrl = out(gc, "Controller")
    bn = call(ped, f"{MOD_C}:BuildNames", "BuildNames"); connect(ctrl, lib.find_self_pin(bn) or pin_in(bn, "self"), "ctrl -> BuildNames"); connect(gid, pin_in(bn, "GuildId"), "g"); connect(then_out(gc), exec_in(bn), "-> BuildNames")
    ba = call(ped, f"{MOD_C}:BuildAllowed", "BuildAllowed"); connect(ctrl, lib.find_self_pin(ba) or pin_in(ba, "self"), "ctrl -> BuildAllowed"); connect(gid, pin_in(ba, "GuildId"), "g"); connect(then_out(bn), exec_in(ba), "-> BuildAllowed")
    # the client event node must exist (compiled) before we can call it
    cev, cnew = event_node("ClientClanTable")
    check(lib.compile_blueprint(pl), "compile (client event available)")
    fname = title(cev)
    cc = call(ped, f"{PL_C}:{fname}", f"call {fname}")
    connect(out(bn, "Names"), pin_in(cc, "Names"), "names"); connect(out(ba, "Allowed"), pin_in(cc, "Allowed"), "allowed"); connect(rank, pin_in(cc, "MyRank"), "rank"); connect(gid, pin_in(cc, "GuildId"), "guild")
    connect(then_out(ba), exec_in(cc), "-> ClientClanTable")
else:
    cev, cnew = event_node("ClientClanTable")

sec("ClientClanTable handler: store cache")
if cnew or not list(PL.list_connected_pins(then_out(cev))):
    tail = then_out(cev)
    for var, param in (("CachedNames", "Names"), ("CachedAllowed", "Allowed"), ("CachedMyRank", "MyRank"), ("CachedGuildId", "GuildId")):
        s = ped.add_set_member_variable_node(var); connect(out(cev, param), pin_in(s, var), f"{param} -> Set {var}"); connect(tail, exec_in(s), f"-> Set {var}"); tail = then_out(s)
    s = ped.add_set_member_variable_node("TableReady"); setval(s, "TableReady", "true"); connect(tail, exec_in(s), "-> TableReady = true")
else: print("   exists")

sec("ServerSetRankName")
ev, new = event_node("ServerSetRankName")
if new:
    tail, pawn, rank, ctl = owner_pawn_rank(ped, then_out(ev))
    gm = call(ped, M + "EqualEqual_ByteByte", "rank==3"); connect(rank, pin_in(gm, "A"), "rank"); setval(gm, "B", "3")
    br = ped.add_branch_node(); connect(tail, exec_in(br), "-> Branch(GM)"); connect(out(gm, "ReturnValue"), lib.find_condition_pin(br), "==3")
    tail, gid = guild_id(ped, pawn, then_out(br))
    gc = call(ped, f"{BPL_C}:GetGAController", "GetGAController"); connect(tail, exec_in(gc), "-> GetGAController")
    srn = call(ped, f"{MOD_C}:SetRankName", "SetRankName"); connect(out(gc, "Controller"), lib.find_self_pin(srn) or pin_in(srn, "self"), "ctrl"); connect(gid, pin_in(srn, "GuildId"), "g")
    connect(out(ev, "Rank"), pin_in(srn, "Rank"), "rank"); connect(out(ev, "Name"), pin_in(srn, "Name"), "name"); connect(then_out(gc), exec_in(srn), "-> SetRankName")

sec("ServerSetTable")
ev, new = event_node("ServerSetTable")
if new:
    tail, pawn, rank, ctl = owner_pawn_rank(ped, then_out(ev))
    gm = call(ped, M + "EqualEqual_ByteByte", "rank==3"); connect(rank, pin_in(gm, "A"), "rank"); setval(gm, "B", "3")
    br = ped.add_branch_node(); connect(tail, exec_in(br), "-> Branch(GM)"); connect(out(gm, "ReturnValue"), lib.find_condition_pin(br), "==3")
    tail, gid = guild_id(ped, pawn, then_out(br))
    gc = call(ped, f"{BPL_C}:GetGAController", "GetGAController"); connect(tail, exec_in(gc), "-> GetGAController")
    lp = forloop(ped, 0, 31); connect(then_out(gc), pin_exact_in(lp, "execute"), "-> ForLoop"); idx = pin_exact_out(lp, "Index")
    sa = call(ped, f"{MOD_C}:SetAllowed", "SetAllowed"); connect(out(gc, "Controller"), lib.find_self_pin(sa) or pin_in(sa, "self"), "ctrl"); connect(gid, pin_in(sa, "GuildId"), "g")
    connect(to_byte(ped, int_div(ped, idx, 4)), pin_in(sa, "Perm"), "perm"); connect(to_byte(ped, int_mod(ped, idx, 4)), pin_in(sa, "Rank"), "rank")
    connect(array_get(ped, out(ev, "Allowed"), idx, "allowed[i]"), pin_in(sa, "Allowed"), "allowed[i]")
    connect(pin_exact_out(lp, "LoopBody"), exec_in(sa), "body -> SetAllowed")

sec("compile")
compile_ok(pl, [(ped, "EventGraph")], "BPC_GA_Player")
print("   events now:", [str(e.name) for e in lib.list_events(pl) if e.is_implemented])
if MODE == "real" and not failures:
    save(mod, os.path.join(DISK_LOCAL, "BP_GA_ModController.uasset"), "BP_GA_ModController")
    save(pl, os.path.join(DISK_LOCAL, "BPC_GA_Player.uasset"), "BPC_GA_Player")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
