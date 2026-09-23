"""Phase 3/5 step A1, authored headlessly. Run WITH -ModDevKit (all three
targets are base-asset overrides, saved through the mod overlay).

GA_MODE=dry    build in memory, compile, dump, save NOTHING
GA_MODE=real   as above, then save all three and verify on disk

What it does
  BP_Master_Placeables        + RequiredRank (Byte, RepNotify, default 0)
  BP_PlaceableItemContainer   CanAccessContainer reads RequiredRank instead of the literal 3
  BP_PL_Door                  Event Custom Interaction gated by rank before the door logic runs
"""
import os, sys, time
import unreal

MODE = os.environ.get("GA_MODE", "dry").lower()
lib, GE, PL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary

MASTER = "/Game/Systems/Building/Placeables/BP_Master_Placeables"
CONT = "/Game/Systems/Building/Placeables/BP_PlaceableItemContainer"
DOOR = "/Game/Systems/Building/Placeables/BP_PL_Door"
BPL_CLASS = "/Game/Mods/GuildAccess/BPL_GuildAccess.BPL_GuildAccess_C"
MODROOT = r"E:\ClaudeCode\conan-exiles\guild-access\GuildAccess\Content\Systems\Building\Placeables"
DISK = {MASTER: os.path.join(MODROOT, "BP_Master_Placeables.uasset"),
        CONT: os.path.join(MODROOT, "BP_PlaceableItemContainer.uasset"),
        DOOR: os.path.join(MODROOT, "BP_PL_Door.uasset")}

failures = []
def sec(t): print("\n======== " + t + " ========")
def check(ok, msg):
    print(("   OK   " if ok else "   FAIL ") + msg)
    if not ok: failures.append(msg)
    return ok
def title(n):
    try: return lib.get_node_title(n)
    except Exception: return n.get_class().get_name()
def node_by_title(ed, t, cls=None):
    hits = [n for n in ed.list_all_nodes() if title(n) == t and (cls is None or n.get_class().get_name() == cls)]
    check(len(hits) == 1, f"exactly one node titled {t!r} (found {len(hits)})")
    return hits[0] if hits else None
def connect(a, b, label):
    return check(a is not None and b is not None and PL.try_create_connection(a, b), f"connect {label}")
def add_call(ed, path, expect_in, expect_out, label):
    try: n = ed.add_call_function_node(path)
    except Exception as e:
        check(False, f"{label}: {path!r} raised {type(e).__name__}: {str(e)[:120]}"); return None
    ok = n is not None and all(lib.find_input_pin(n, p) is not None for p in expect_in) and all(lib.find_output_pin(n, p) is not None for p in expect_out)
    if not ok and n is not None:
        try: ed.remove_nodes([n])
        except Exception: pass
    check(ok, f"{label}: created via {path!r}")
    return n if ok else None
def dump(ed, name, only_titles=None):
    print(f"   --- dump {name} ---")
    for n in ed.list_all_nodes():
        t = title(n)
        if only_titles and not any(k in t for k in only_titles): continue
        print(f"   NODE [{n.get_class().get_name()}] {t!r}")
        for p in lib.list_all_pins(n):
            d = str(PL.get_pin_direction(p)).replace("EdGraphPinDirection.", "")
            v = PL.get_pin_value(p)
            conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
            if v or conns: print(f"      {str(PL.get_pin_name(p)):24} {d:11} val={v!r:8} -> {conns}")

sec(f"mode = {MODE}")
if MODE not in ("dry", "real"): print("bad GA_MODE"); sys.exit(2)
st0 = {k: (os.stat(v).st_mtime if os.path.exists(v) else None) for k, v in DISK.items()}
for k, v in st0.items(): print(f"   pre: {os.path.basename(DISK[k]):34} {'exists' if v else 'ABSENT (new override)'}")

# ---------------------------------------------------------------- Master: variable
sec("BP_Master_Placeables :: RequiredRank")
master = unreal.load_asset(MASTER)
check(master is not None, "loaded BP_Master_Placeables")
names = [str(x) for x in lib.list_member_variable_names(master)]
if "RequiredRank" in names or any(x.endswith(".RequiredRank") for x in names):
    print("   RequiredRank already present")
else:
    check(lib.add_member_variable(master, "RequiredRank", lib.get_basic_type_by_name("byte")), "add_member_variable RequiredRank (byte)")
try:
    lib.set_blueprint_variable_replication(master, "RequiredRank", unreal.BlueprintVariableReplication.REP_NOTIFY)
    rep = lib.get_blueprint_variable_replication(master, "RequiredRank")
    check(rep == unreal.BlueprintVariableReplication.REP_NOTIFY or "REP_NOTIFY" in str(rep), f"RequiredRank replication = RepNotify (got {rep})")
except Exception as e:
    check(False, f"set replication raised {type(e).__name__}: {str(e)[:120]}")
try: lib.set_blueprint_variable_instance_editable(master, "RequiredRank", False)
except Exception: pass
print("   Master graphs now:", [g for g in [str(x) for x in lib.list_graph_names(master)] if "RequiredRank" in g or "Interactable" in g])
# events present on Master's EventGraph (informs where menu/activate overrides can go later)
edm = GE.get_graph_editor_by_name(master, "EventGraph")
evs = [title(n) for n in edm.list_all_nodes() if n.get_class().get_name() == "K2Node_Event"]
print("   Master EventGraph events:", [e for e in evs if "Interactable" in e or "Custom" in e] or "(none interaction-related)")
check(lib.compile_blueprint(master), "compile Master")

# ---------------------------------------------------------------- Container: read the variable
sec("BP_PlaceableItemContainer :: CanAccessContainer reads RequiredRank")
cont = unreal.load_asset(CONT)
check(cont is not None, "loaded container override")
ed = GE.get_graph_editor_by_name(cont, "CanAccessContainer")
mrr = node_by_title(ed, "MeetsRankRequirement")
if mrr:
    req = lib.find_input_pin(mrr, "Required")
    if PL.list_connected_pins(req):
        print("   Required already wired; leaving")
    else:
        getter = None
        for cp in ("", MASTER + ".BP_Master_Placeables_C"):
            try:
                getter = ed.add_get_member_variable_node("RequiredRank", cp)
            except Exception as e:
                print(f"      class_path={cp!r}: {type(e).__name__}"); getter = None
            if getter and lib.find_output_pin(getter, "RequiredRank") is not None:
                print(f"      getter created (class_path={cp!r})"); break
            if getter:
                try: ed.remove_nodes([getter])
                except Exception: pass
                getter = None
        check(getter is not None, "Get RequiredRank node")
        if getter:
            connect(lib.find_output_pin(getter, "RequiredRank"), req, "RequiredRank -> MeetsRankRequirement.Required")
dump(ed, "CanAccessContainer", only_titles=("MeetsRankRequirement", "RequiredRank"))
check(lib.compile_blueprint(cont), "compile container")
check(len(list(ed.list_nodes_with_errors())) == 0, "CanAccessContainer: no error nodes")

# ---------------------------------------------------------------- Door: gate Custom Interaction
sec("BP_PL_Door :: gate Event Custom Interaction")
door = unreal.load_asset(DOOR)
check(door is not None, "loaded BP_PL_Door")
edd = GE.get_graph_editor_by_name(door, "EventGraph")
ev = node_by_title(edd, "Event Custom Interaction", "K2Node_Event")
if ev and not any(title(n) == "GetPawnRank" for n in edd.list_all_nodes()):
    ev_then = lib.find_then_pin(ev)
    ev_inst = lib.find_output_pin(ev, "Instigator")
    targets = list(PL.list_connected_pins(ev_then))
    check(len(targets) == 1, f"Custom Interaction.then has exactly one target (found {len(targets)})")
    orig = targets[0] if targets else None
    print("      original target:", f"{title(PL.get_owning_node(orig))}.{PL.get_pin_name(orig)}" if orig else None)

    getpawn = add_call(edd, "/Script/Engine.Controller:K2_GetPawn", [], ["ReturnValue"], "Get Controlled Pawn")
    gpr = add_call(edd, BPL_CLASS + ":GetPawnRank", ["Pawn"], ["Rank"], "GetPawnRank")
    igmr = add_call(edd, BPL_CLASS + ":IsGuildMemberRank", ["Rank"], ["Result"], "IsGuildMemberRank")
    mrr2 = add_call(edd, BPL_CLASS + ":MeetsRankRequirement", ["Rank", "Required"], ["Result"], "MeetsRankRequirement")
    notn = add_call(edd, "/Script/Engine.KismetMathLibrary:Not_PreBool", ["A"], ["ReturnValue"], "NOT")
    orn = add_call(edd, "/Script/Engine.KismetMathLibrary:BooleanOR", ["A", "B"], ["ReturnValue"], "OR")
    getreq = None
    try:
        getreq = edd.add_get_member_variable_node("RequiredRank", "")
        if getreq and lib.find_output_pin(getreq, "RequiredRank") is None:
            edd.remove_nodes([getreq]); getreq = edd.add_get_member_variable_node("RequiredRank", MASTER + ".BP_Master_Placeables_C")
    except Exception as e:
        print("      get RequiredRank raised", type(e).__name__)
    check(getreq is not None and lib.find_output_pin(getreq, "RequiredRank") is not None, "Get RequiredRank node (door)")
    branch = edd.add_branch_node()
    check(branch is not None, "Branch")

    if all(x is not None for x in (getpawn, gpr, igmr, mrr2, notn, orn, getreq, branch, orig)):
        PL.break_pin_links(ev_then)
        connect(ev_inst, lib.find_input_pin(getpawn, "self"), "Instigator -> GetPawn.self")
        connect(ev_then, lib.find_execute_pin(gpr), "Custom Interaction.then -> GetPawnRank")
        connect(lib.find_output_pin(getpawn, "ReturnValue"), lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank.Pawn")
        connect(lib.find_then_pin(gpr), lib.find_execute_pin(igmr), "GetPawnRank -> IsGuildMemberRank")
        connect(lib.find_output_pin(gpr, "Rank"), lib.find_input_pin(igmr, "Rank"), "rank -> IsGuildMemberRank.Rank")
        connect(lib.find_then_pin(igmr), lib.find_execute_pin(mrr2), "IsGuildMemberRank -> MeetsRankRequirement")
        connect(lib.find_output_pin(gpr, "Rank"), lib.find_input_pin(mrr2, "Rank"), "rank -> MeetsRankRequirement.Rank")
        connect(lib.find_output_pin(getreq, "RequiredRank"), lib.find_input_pin(mrr2, "Required"), "RequiredRank -> Required")
        connect(lib.find_output_pin(igmr, "Result"), lib.find_input_pin(notn, "A"), "member -> NOT")
        connect(lib.find_output_pin(notn, "ReturnValue"), lib.find_input_pin(orn, "A"), "NOT -> OR.A")
        connect(lib.find_output_pin(mrr2, "Result"), lib.find_input_pin(orn, "B"), "meets -> OR.B")
        connect(lib.find_then_pin(mrr2), lib.find_execute_pin(branch), "MeetsRankRequirement -> Branch")
        connect(lib.find_output_pin(orn, "ReturnValue"), lib.find_condition_pin(branch), "OR -> Branch.Condition")
        connect(lib.find_then_pin(branch), orig, "Branch.True -> original door logic")
        # Branch.False deliberately unconnected: denied = door does nothing (v1; message is a follow-up)
elif ev:
    print("   door already gated; leaving")
dump(edd, "door gate", only_titles=("Custom Interaction", "GetPawnRank", "IsGuildMemberRank", "MeetsRankRequirement", "NOT Boolean", "OR Boolean", "Branch", "RequiredRank", "Get Controlled Pawn"))
check(lib.compile_blueprint(door), "compile door")
check(len(list(edd.list_nodes_with_errors())) == 0, "door EventGraph: no error nodes")

# ---------------------------------------------------------------- save
if MODE == "real" and not failures:
    sec("save (mod overlay remap)")
    pkgs = [b.get_outermost() for b in (master, cont, door)]
    r = unreal.EditorLoadingAndSavingUtils.save_packages(pkgs, False)
    print("   save_packages ->", r)
    for k, v in DISK.items():
        exists = os.path.exists(v)
        changed = exists and (st0[k] is None or os.stat(v).st_mtime > st0[k])
        check(changed, f"{os.path.basename(v)} written to the mod overlay ({time.strftime('%H:%M:%S', time.localtime(os.stat(v).st_mtime)) if exists else 'missing'})")
elif MODE == "real":
    sec("NOT SAVING - failures"); [print("   -", f) for f in failures]

sec("RESULT: " + ("ALL OK" if not failures else f"{len(failures)} FAILURE(S)") + (" (dry run, nothing saved)" if MODE == "dry" else ""))
for f in failures: print("   -", f)
sys.exit(0 if not failures else 1)
