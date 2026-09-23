"""A2 part 1a - BPL_GuildAccess additions. Run WITHOUT -ModDevKit.
GA_MODE=dry | real.  Adds RankToText(Rank)->Text and RankCanSetRequired(Rank, CurrentRequired)->Bool."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

BPL_PATH = f"{LOCAL}/BPL_GuildAccess"
sec(f"mode = {MODE}")
if MODE not in ("dry", "real"): print("unknown GA_MODE"); sys.exit(2)

sec("BPL_GuildAccess :: RankToText + RankCanSetRequired")
bpl = unreal.load_asset(BPL_PATH); check(bpl is not None, "loaded BPL_GuildAccess")
names = [str(x) for x in lib.list_graph_names(bpl)]
eds = []
byte_t, bool_t, text_t = lib.get_basic_type_by_name("byte"), lib.get_basic_type_by_name("bool"), lib.get_basic_type_by_name("text")

if "RankToText" in names:
    print("   RankToText exists; leaving as is"); ed = GE.get_graph_editor_by_name(bpl, "RankToText")
else:
    g = lib.add_function_graph(bpl, "RankToText"); ed = GE.get_graph_editor(g)
    ed.set_is_pure_function(True)
    rank = ed.add_graph_input_parameter("Rank", byte_t, "")
    ret = ed.add_graph_output_parameter("Result", text_t)
    check(rank is not None and ret is not None, "RankToText params")
    eqs = {}
    for v in (1, 2, 3):
        e = call(ed, "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte", f"EqualEqual_ByteByte({v})")
        connect(rank, lib.find_input_pin(e, "A"), f"Rank -> ==.A ({v})"); setval(e, "B", str(v)); eqs[v] = e
    s1 = call(ed, "/Script/Engine.KismetMathLibrary:SelectText", "SelectText 1")
    s2 = call(ed, "/Script/Engine.KismetMathLibrary:SelectText", "SelectText 2")
    s3 = call(ed, "/Script/Engine.KismetMathLibrary:SelectText", "SelectText 3")
    setval(s1, "A", text_lit("RankMember", "Member")); setval(s1, "B", text_lit("RankRecruit", "Recruit"))
    connect(lib.find_output_pin(eqs[1], "ReturnValue"), lib.find_input_pin(s1, "bPickA"), "==1 -> S1.bPickA")
    setval(s2, "A", text_lit("RankOfficer", "Officer"))
    connect(lib.find_output_pin(s1, "ReturnValue"), lib.find_input_pin(s2, "B"), "S1 -> S2.B")
    connect(lib.find_output_pin(eqs[2], "ReturnValue"), lib.find_input_pin(s2, "bPickA"), "==2 -> S2.bPickA")
    setval(s3, "A", text_lit("RankGuildMaster", "Guild Master"))
    connect(lib.find_output_pin(s2, "ReturnValue"), lib.find_input_pin(s3, "B"), "S2 -> S3.B")
    connect(lib.find_output_pin(eqs[3], "ReturnValue"), lib.find_input_pin(s3, "bPickA"), "==3 -> S3.bPickA")
    connect(lib.find_output_pin(s3, "ReturnValue"), lib.find_input_pin(ret, "Result"), "S3 -> Result")
    ep = ed.find_graph_entry_pin()
    if ep is not None and lib.find_execute_pin(ret) is not None:
        PL.try_create_connection(ep, lib.find_execute_pin(ret)); print("      (exec pins present; wired entry->return)")
eds.append((ed, "RankToText")); dump(ed, "RankToText")

if "RankCanSetRequired" in names:
    print("   RankCanSetRequired exists; leaving as is"); ed2 = GE.get_graph_editor_by_name(bpl, "RankCanSetRequired")
else:
    g = lib.add_function_graph(bpl, "RankCanSetRequired"); ed2 = GE.get_graph_editor(g)
    ed2.set_is_pure_function(True)
    rank = ed2.add_graph_input_parameter("Rank", byte_t, "")
    cur = ed2.add_graph_input_parameter("CurrentRequired", byte_t, "")
    ret = ed2.add_graph_output_parameter("Result", bool_t)
    check(rank is not None and cur is not None and ret is not None, "RankCanSetRequired params")
    le = call(ed2, "/Script/Engine.KismetMathLibrary:LessEqual_ByteByte", "Rank <= 3 (member)")
    connect(rank, lib.find_input_pin(le, "A"), "Rank -> <=.A"); setval(le, "B", "3")
    ge_cur = call(ed2, "/Script/Engine.KismetMathLibrary:GreaterEqual_ByteByte", "Rank >= Current")
    connect(rank, lib.find_input_pin(ge_cur, "A"), "Rank -> >=cur.A"); connect(cur, lib.find_input_pin(ge_cur, "B"), "Current -> >=cur.B")
    ge_off = call(ed2, "/Script/Engine.KismetMathLibrary:GreaterEqual_ByteByte", "Rank >= Officer")
    connect(rank, lib.find_input_pin(ge_off, "A"), "Rank -> >=2.A"); setval(ge_off, "B", "2")
    a1 = call(ed2, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND 1"); a2 = call(ed2, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND 2")
    connect(lib.find_output_pin(le, "ReturnValue"), lib.find_input_pin(a1, "A"), "<=3 -> AND1.A")
    connect(lib.find_output_pin(ge_cur, "ReturnValue"), lib.find_input_pin(a1, "B"), ">=cur -> AND1.B")
    connect(lib.find_output_pin(a1, "ReturnValue"), lib.find_input_pin(a2, "A"), "AND1 -> AND2.A")
    connect(lib.find_output_pin(ge_off, "ReturnValue"), lib.find_input_pin(a2, "B"), ">=2 -> AND2.B")
    connect(lib.find_output_pin(a2, "ReturnValue"), lib.find_input_pin(ret, "Result"), "AND2 -> Result")
    ep = ed2.find_graph_entry_pin()
    if ep is not None and lib.find_execute_pin(ret) is not None: PL.try_create_connection(ep, lib.find_execute_pin(ret))
eds.append((ed2, "RankCanSetRequired")); dump(ed2, "RankCanSetRequired")
compile_ok(bpl, eds, "BPL_GuildAccess")

# is the new function actually pure? (a call node without an execute pin)
probe_ed = GE.get_graph_editor_by_name(bpl, "GetPawnRank")
n = probe_ed.add_call_function_node(f"{BPL_PATH}.BPL_GuildAccess_C:RankToText")
if n: print("   RankToText call-node pins:", pins(n), "-> pure =", lib.find_execute_pin(n) is None); probe_ed.remove_nodes([n])
n = probe_ed.add_call_function_node(f"{BPL_PATH}.BPL_GuildAccess_C:RankCanSetRequired")
if n: print("   RankCanSetRequired call-node pins:", pins(n), "-> pure =", lib.find_execute_pin(n) is None); probe_ed.remove_nodes([n])

if MODE == "real" and not failures:
    sec("save BPL_GuildAccess")
    save(bpl, os.path.join(DISK_LOCAL, "BPL_GuildAccess.uasset"), "BPL_GuildAccess")
elif MODE == "real": print("\n   NOT SAVING: failures above")
result()
