"""v2 stage 1 - per-clan rank names + permission table, stored on the ModController.
Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

BPL_GuildAccess (+):
  GAKey2(GuildId:string (guild StableId), A:byte) -> String            "<g>:<a>"
  GAKey3(GuildId:string, A:byte, B:byte) -> String    "<g>:<a>:<b>"
  DefaultAllowed(Perm:byte, Rank:byte) -> Bool     vanilla-equivalent defaults (pure)
  PermToText(Perm:byte) -> Text                    row labels (pure)
  GetGAController() -> BP_GA_ModController         first instance in the world

BP_GA_ModController (+):
  RankNames : Map<String,String>   key GAKey2(guild, rank)         (SaveGame: GUI tick)
  Perms     : Map<String,Bool>     key GAKey3(guild, perm, rank)   (SaveGame: GUI tick)
  GetRankName(GuildId, Rank) -> String     stored name or the vanilla one
  IsAllowed(GuildId, Perm, Rank) -> Bool   Guild Master always true; stored value or DefaultAllowed
  SetRankName(GuildId, Rank, Name)         server only (callers check); marks persistence dirty
  SetAllowed(GuildId, Perm, Rank, Allowed) server only (callers check); marks persistence dirty

Permission ids (byte): 0 Dismantle, 1 PickUp, 2 Move, 3 Repair, 4 Upgrade, 5 SetAccessRank, 6 EditRankNames, 7 EditTable
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

BPL_PATH = f"{LOCAL}/BPL_GuildAccess"; BPL_C = f"{BPL_PATH}.BPL_GuildAccess_C"
MOD_PATH = f"{LOCAL}/BP_GA_ModController"; MOD_C = f"{MOD_PATH}.BP_GA_ModController_C"
PERMS = ["Dismantle", "Pick up", "Move", "Repair", "Upgrade", "Set access rank", "Edit rank names", "Edit this table"]
byte_t, bool_t, int_t, str_t, text_t = [lib.get_basic_type_by_name(x) for x in ("byte", "bool", "int", "string", "text")]
M = "/Script/Engine.KismetMathLibrary:"; S = "/Script/Engine.KismetStringLibrary:"; T = "/Script/Engine.KismetTextLibrary:"

sec(f"mode = {MODE}")
wait_registry()
bpl = unreal.load_asset(BPL_PATH); mod = unreal.load_asset(MOD_PATH)
check(bpl is not None and mod is not None, "loaded BPL + ModController")
mod_cls = lib.generated_class(mod)
# recreate the guild-keyed graphs from scratch (GuildId type changed): remove dependents first, then compile both
for bp_, names_ in ((mod, ("GetRankName", "IsAllowed", "SetRankName", "SetAllowed", "BuildAllowed", "BuildNames")), (bpl, ("GAKey2", "GAKey3"))):
    for nm in names_:
        if nm in [str(x) for x in lib.list_graph_names(bp_)]: lib.remove_function_graph(bp_, nm); print(f"   removed {nm} for recreation")
check(lib.compile_blueprint(mod), "ModController compiles without the old graphs"); check(lib.compile_blueprint(bpl), "BPL compiles without the old graphs")

def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
RECREATE = {"GAKey2", "GAKey3", "GetRankName", "IsAllowed", "SetRankName", "SetAllowed"}
def fn_graph(bp, name, inputs, outputs, pure=False):
    """returns (editor, {input pins}, return node, created?)"""
    names = [str(x) for x in lib.list_graph_names(bp)]
    if name in names: return GE.get_graph_editor_by_name(bp, name), None, None, False
    g = lib.add_function_graph(bp, name); ed = GE.get_graph_editor(g)
    if pure: ed.set_is_pure_function(True)
    ins = {n: ed.add_graph_input_parameter(n, t, "") for n, t in inputs}
    ret = None
    for n, t in outputs: ret = ed.add_graph_output_parameter(n, t)
    check(all(v is not None for v in ins.values()) and (ret is not None or not outputs), f"{name}: params")
    return ed, ins, ret, True
def wire_exec(ed, ret):
    ep = ed.find_graph_entry_pin()
    if ep is not None and ret is not None and exec_in(ret) is not None and not list(PL.list_connected_pins(ep)): PL.try_create_connection(ep, exec_in(ret))
def int_to_str(ed, pin):
    n = call(ed, S + "Conv_IntToString", "IntToString"); connect(pin, lib.find_input_pin(n, "InInt"), "-> IntToString"); return out(n, "ReturnValue")
def byte_to_str(ed, pin):
    b = call(ed, M + "Conv_ByteToInt", "ByteToInt"); connect(pin, lib.find_input_pin(b, "InByte"), "-> ByteToInt"); return int_to_str(ed, out(b, "ReturnValue"))
def concat(ed, a_pin, b_pin=None, b_lit=None):
    c = call(ed, S + "Concat_StrStr", "Concat"); connect(a_pin, lib.find_input_pin(c, "A"), "-> Concat.A")
    if b_pin is not None: connect(b_pin, lib.find_input_pin(c, "B"), "-> Concat.B")
    else: setval(c, "B", b_lit)
    return out(c, "ReturnValue")

# ============================================================= BPL helpers
sec("BPL: GAKey2 / GAKey3 / DefaultAllowed / PermToText / GetGAController")
ed, ins, ret, new = fn_graph(bpl, "GAKey2", [("GuildId", str_t), ("A", byte_t)], [("Key", str_t)], pure=True)
if new:
    g = concat(ed, ins["GuildId"], b_lit=":"); k = concat(ed, g, byte_to_str(ed, ins["A"]))
    connect(k, lib.find_input_pin(ret, "Key"), "key -> Return"); wire_exec(ed, ret)
ed, ins, ret, new = fn_graph(bpl, "GAKey3", [("GuildId", str_t), ("A", byte_t), ("B", byte_t)], [("Key", str_t)], pure=True)
if new:
    g = concat(ed, ins["GuildId"], b_lit=":"); k1 = concat(ed, g, byte_to_str(ed, ins["A"])); k2 = concat(ed, k1, b_lit=":"); k = concat(ed, k2, byte_to_str(ed, ins["B"]))
    connect(k, lib.find_input_pin(ret, "Key"), "key -> Return"); wire_exec(ed, ret)
ed, ins, ret, new = fn_graph(bpl, "DefaultAllowed", [("Perm", byte_t), ("Rank", byte_t)], [("Allowed", bool_t)], pure=True)
if new:
    # threshold rank: Repair(3)->0 ; Dismantle/PickUp/Move(0-2)->1 ; Upgrade/SetAccessRank(4-5)->2 ; EditNames/EditTable(6-7)->3
    le2 = call(ed, M + "LessEqual_ByteByte", "Perm<=2"); connect(ins["Perm"], lib.find_input_pin(le2, "A"), "Perm"); setval(le2, "B", "2")
    le5 = call(ed, M + "LessEqual_ByteByte", "Perm<=5"); connect(ins["Perm"], lib.find_input_pin(le5, "A"), "Perm"); setval(le5, "B", "5")
    eq3 = call(ed, M + "EqualEqual_ByteByte", "Perm==3"); connect(ins["Perm"], lib.find_input_pin(eq3, "A"), "Perm"); setval(eq3, "B", "3")
    s1 = call(ed, M + "SelectInt", "sel 1/3"); setval(s1, "A", "1"); setval(s1, "B", "3"); connect(out(le2, "ReturnValue"), lib.find_input_pin(s1, "bPickA"), "<=2 -> pick")
    s2 = call(ed, M + "SelectInt", "sel 2/s1"); setval(s2, "A", "2"); connect(out(s1, "ReturnValue"), lib.find_input_pin(s2, "B"), "s1 -> B")
    ge4 = call(ed, M + "GreaterEqual_ByteByte", "Perm>=4"); connect(ins["Perm"], lib.find_input_pin(ge4, "A"), "Perm"); setval(ge4, "B", "4")
    a45 = call(ed, M + "BooleanAND", "4..5"); connect(out(ge4, "ReturnValue"), lib.find_input_pin(a45, "A"), ">=4"); connect(out(le5, "ReturnValue"), lib.find_input_pin(a45, "B"), "<=5")
    connect(out(a45, "ReturnValue"), lib.find_input_pin(s2, "bPickA"), "4..5 -> pick")
    s3 = call(ed, M + "SelectInt", "sel 0/s2"); setval(s3, "A", "0"); connect(out(s2, "ReturnValue"), lib.find_input_pin(s3, "B"), "s2 -> B"); connect(out(eq3, "ReturnValue"), lib.find_input_pin(s3, "bPickA"), "==3 -> pick")
    r2i = call(ed, M + "Conv_ByteToInt", "Rank->int"); connect(ins["Rank"], lib.find_input_pin(r2i, "InByte"), "Rank")
    ge = call(ed, M + "GreaterEqual_IntInt", "rank >= threshold"); connect(out(r2i, "ReturnValue"), lib.find_input_pin(ge, "A"), "rank"); connect(out(s3, "ReturnValue"), lib.find_input_pin(ge, "B"), "threshold")
    connect(out(ge, "ReturnValue"), lib.find_input_pin(ret, "Allowed"), "-> Return"); wire_exec(ed, ret)
ed, ins, ret, new = fn_graph(bpl, "PermToText", [("Perm", byte_t)], [("Result", text_t)], pure=True)
if new:
    prev = None
    for i in range(len(PERMS) - 1, -1, -1):   # SelectText chain, innermost first
        sel = call(ed, M + "SelectText", f"SelectText {i}"); setval(sel, "A", text_lit(f"Perm{i}", PERMS[i]))
        if prev is None: setval(sel, "B", text_lit("PermUnknown", "?"))
        else: connect(prev, lib.find_input_pin(sel, "B"), "chain")
        eq = call(ed, M + "EqualEqual_ByteByte", f"Perm=={i}"); connect(ins["Perm"], lib.find_input_pin(eq, "A"), "Perm"); setval(eq, "B", str(i)); connect(out(eq, "ReturnValue"), lib.find_input_pin(sel, "bPickA"), "pick")
        prev = out(sel, "ReturnValue")
    connect(prev, lib.find_input_pin(ret, "Result"), "-> Return"); wire_exec(ed, ret)
ed, ins, ret, new = fn_graph(bpl, "GetGAController", [], [("Controller", lib.get_object_reference_type(mod_cls))])
if new:
    gaa = call(ed, "/Script/Engine.GameplayStatics:GetAllActorsOfClass", "GetAllActorsOfClass"); setval(gaa, "ActorClass", MOD_C)
    arr = out(gaa, "OutActors")
    get = create_by_search(ed, [arr], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)", "|Get"])
    print("   array get pins:", pins(get) if get else None)
    arr_in = next((p for p in lib.list_input_pins(get) if "Array" in str(PL.get_pin_name(p)) or str(PL.get_pin_name(p)) == "TargetArray"), None)
    connect(arr, arr_in, "OutActors -> Get.array")
    idx = next((p for p in lib.list_input_pins(get) if "Index" in str(PL.get_pin_name(p))), None)
    if idx is not None: PL.set_pin_value(idx, "0")
    connect(out(get), lib.find_input_pin(ret, "Controller"), "Get[0] -> Return")
    connect(ed.find_graph_entry_pin(), exec_in(gaa), "entry -> GetAllActorsOfClass"); connect(then_out(gaa), exec_in(ret), "-> Return")
compile_ok(bpl, [], "BPL_GuildAccess")

# ============================================================= ModController data
sec("ModController: maps")
have = [str(v) for v in lib.list_member_variable_names(mod)]
if "RankNames" not in have: check(lib.add_member_variable(mod, "RankNames", lib.get_map_type(str_t, str_t)), "RankNames map")
if "Perms" not in have: check(lib.add_member_variable(mod, "Perms", lib.get_map_type(str_t, bool_t)), "Perms map")
check(lib.compile_blueprint(mod), "compile after maps")

sec("ModController: GetRankName")
ed, ins, ret, new = fn_graph(mod, "GetRankName", [("GuildId", str_t), ("Rank", byte_t)], [("Name", str_t)])
if new:
    key = call(ed, f"{BPL_C}:GAKey2", "GAKey2"); connect(ins["GuildId"], lib.find_input_pin(key, "GuildId"), "g"); connect(ins["Rank"], lib.find_input_pin(key, "A"), "r")
    m = ed.add_get_member_variable_node("RankNames")
    find = create_by_search(ed, [out(m)], ("Map", "Find"), "Map Find", exact="Utilities|Map|Find"); print("   Map Find pins:", pins(find))
    connect(out(m), next(p for p in lib.list_input_pins(find) if "Map" in str(PL.get_pin_name(p))), "map -> Find")
    connect(out(key, "Key"), lib.find_input_pin(find, "Key"), "key -> Find")
    br = ed.add_branch_node(); connect(ed.find_graph_entry_pin(), exec_in(br), "entry -> Branch"); connect(out(find, "ReturnValue"), lib.find_condition_pin(br), "found -> cond")
    connect(then_out(br), exec_in(ret), "found -> Return"); connect(out(find, "Value"), lib.find_input_pin(ret, "Name"), "value -> Name")
    ret2 = ed.add_return_node(); connect(lib.find_else_pin(br), exec_in(ret2), "not found -> Return(default)")
    rt = call(ed, f"{BPL_C}:RankToText", "RankToText"); connect(ins["Rank"], lib.find_input_pin(rt, "Rank"), "rank")
    t2s = call(ed, T + "Conv_TextToString", "TextToString"); connect(out(rt, "Result"), lib.find_input_pin(t2s, "InText"), "-> str"); connect(out(t2s, "ReturnValue"), lib.find_input_pin(ret2, "Name"), "default -> Name")

sec("ModController: IsAllowed")
ed, ins, ret, new = fn_graph(mod, "IsAllowed", [("GuildId", str_t), ("Perm", byte_t), ("Rank", byte_t)], [("Allowed", bool_t)])
if new:
    gm = call(ed, M + "EqualEqual_ByteByte", "Rank==3"); connect(ins["Rank"], lib.find_input_pin(gm, "A"), "rank"); setval(gm, "B", "3")
    br0 = ed.add_branch_node(); connect(ed.find_graph_entry_pin(), exec_in(br0), "entry -> Branch(GM)"); connect(out(gm, "ReturnValue"), lib.find_condition_pin(br0), "==3")
    connect(then_out(br0), exec_in(ret), "GM -> Return"); setval(ret, "Allowed", "true")
    key = call(ed, f"{BPL_C}:GAKey3", "GAKey3"); connect(ins["GuildId"], lib.find_input_pin(key, "GuildId"), "g"); connect(ins["Perm"], lib.find_input_pin(key, "A"), "p"); connect(ins["Rank"], lib.find_input_pin(key, "B"), "r")
    m = ed.add_get_member_variable_node("Perms")
    find = create_by_search(ed, [out(m)], ("Map", "Find"), "Map Find", exact="Utilities|Map|Find")
    connect(out(m), next(p for p in lib.list_input_pins(find) if "Map" in str(PL.get_pin_name(p))), "map -> Find"); connect(out(key, "Key"), lib.find_input_pin(find, "Key"), "key -> Find")
    br1 = ed.add_branch_node(); connect(lib.find_else_pin(br0), exec_in(br1), "not GM -> Branch(found)"); connect(out(find, "ReturnValue"), lib.find_condition_pin(br1), "found")
    ret1 = ed.add_return_node(); connect(then_out(br1), exec_in(ret1), "found -> Return(value)"); connect(out(find, "Value"), lib.find_input_pin(ret1, "Allowed"), "value")
    ret2 = ed.add_return_node(); connect(lib.find_else_pin(br1), exec_in(ret2), "not found -> Return(default)")
    da = call(ed, f"{BPL_C}:DefaultAllowed", "DefaultAllowed"); connect(ins["Perm"], lib.find_input_pin(da, "Perm"), "p"); connect(ins["Rank"], lib.find_input_pin(da, "Rank"), "r"); connect(out(da, "Allowed"), lib.find_input_pin(ret2, "Allowed"), "default")

def setter(name, inputs, mapvar, keyfn, keyargs, valname):
    sec(f"ModController: {name}")
    ed, ins, ret, new = fn_graph(mod, name, inputs, [])
    if not new: return
    key = call(ed, f"{BPL_C}:{keyfn}", keyfn)
    for a, b in keyargs: connect(ins[a], lib.find_input_pin(key, b), f"{a} -> key.{b}")
    m = ed.add_get_member_variable_node(mapvar)
    add = create_by_search(ed, [out(m)], ("Map", "Add"), "Map Add", exact="Utilities|Map|Add"); print("   Map Add pins:", pins(add))
    connect(out(m), next(p for p in lib.list_input_pins(add) if "Map" in str(PL.get_pin_name(p))), "map -> Add"); connect(out(key, "Key"), lib.find_input_pin(add, "Key"), "key -> Add")
    connect(ins[valname], lib.find_input_pin(add, "Value"), "value -> Add")
    connect(ed.find_graph_entry_pin(), exec_in(add), "entry -> Add")
    pc = ed.add_get_member_variable_node("PersistenceComponent")
    sd = create_by_search(ed, [out(pc)], ("SetDirty",), "SetDirty")
    if sd is not None:
        sp = lib.find_self_pin(sd) or lib.find_input_pin(sd, "self")
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(pc), sp, "persistence -> SetDirty.self")
        setval(sd, "bDirty", "true"); connect(then_out(add), exec_in(sd), "Add -> SetDirty")
        r = ed.add_return_node(); connect(then_out(sd), exec_in(r), "-> Return")
    else:
        r = ed.add_return_node(); connect(then_out(add), exec_in(r), "-> Return")
setter("SetRankName", [("GuildId", str_t), ("Rank", byte_t), ("Name", str_t)], "RankNames", "GAKey2", [("GuildId", "GuildId"), ("Rank", "A")], "Name")
setter("SetAllowed", [("GuildId", str_t), ("Perm", byte_t), ("Rank", byte_t), ("Allowed", bool_t)], "Perms", "GAKey3", [("GuildId", "GuildId"), ("Perm", "A"), ("Rank", "B")], "Allowed")

sec("compile")
compile_ok(mod, [(GE.get_graph_editor_by_name(mod, g), g) for g in ("GetRankName", "IsAllowed", "SetRankName", "SetAllowed")], "BP_GA_ModController")
compile_ok(bpl, [(GE.get_graph_editor_by_name(bpl, g), g) for g in ("GAKey2", "GAKey3", "DefaultAllowed", "PermToText", "GetGAController")], "BPL_GuildAccess")
if MODE == "real" and not failures:
    save(bpl, os.path.join(DISK_LOCAL, "BPL_GuildAccess.uasset"), "BPL_GuildAccess")
    save(mod, os.path.join(DISK_LOCAL, "BP_GA_ModController.uasset"), "BP_GA_ModController")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
