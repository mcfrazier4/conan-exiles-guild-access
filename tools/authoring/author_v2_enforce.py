"""v2 stage 3 - server-side enforcement of dismantle (perm 0) and pick-up (perm 1) on
placeables. Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=container|door. Idempotent.

On the leaf override:
  GetCanBeDismantled(DismantlingCharacter) -> Parent AND (not a member OR (rank >= RequiredRank AND IsAllowed(guild, 0, rank)))
  CanReturnToInventory(ownerCharacter)     -> Parent AND (not a member OR (rank >= RequiredRank AND IsAllowed(guild, 1, rank)))
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "container").lower()
CLASSES = {"container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
           "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset")}
PATH, REL = CLASSES[TARGET]; DISK = os.path.join(DISK_CONTENT, REL)
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"; MOD_C = f"{LOCAL}/BP_GA_ModController.BP_GA_ModController_C"
M = "/Script/Engine.KismetMathLibrary:"
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
bp = unreal.load_asset(PATH); check(bp is not None, "loaded")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin_in(n, *names):
    for nm in names:
        p = lib.find_input_pin(n, nm)
        if p is not None: return p
    return None

def gate(fname, perm, result_pin_name):
    sec(f"{fname} (perm {perm})")
    names = [str(x) for x in lib.list_graph_names(bp)]
    if fname not in names:
        g = lib.add_function_override(bp, fname); check(g is not None, f"override {fname}")
    ed = GE.get_graph_editor_by_name(bp, fname); check(ed is not None, "editor")
    if nodes_titled(ed, "IsAllowed"): print("   exists"); return ed
    for v in nodes_titled(ed, "Get CanBeDismantled"): ed.remove_nodes([v])   # drop the interim wiring if we are completing the graph
    lib.compile_blueprint(bp)
    entry = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionEntry"][0]
    params = [p for p in lib.list_output_pins(entry) if str(PL.get_pin_name(p)) != "then"]
    print("   entry pins:", pins(entry))
    char = params[0] if params else None; check(char is not None, f"character param ({[str(PL.get_pin_name(p)) for p in params]})")
    rets = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"]
    parent = nodes_titled(ed, f"Parent: {fname}")
    if not parent:
        print("   parent-ish actions:", [a for a in available(ed, []) if "parent" in a.lower() and fname.lower() in a.lower()][:5], "| entry->", [title(PL.get_owning_node(c)) for c in PL.list_connected_pins(ed.find_graph_entry_pin())])
        hits = [a for a in available(ed, []) if "parent" in a.lower() and fname.lower() in a.lower()]
        if hits:
            n = ed.create_node_from_name(hits[0], unreal.Vector2D(0, 0), []); parent = [n] if n else []
    if not parent:
        # interim: behave exactly like vanilla (return the inherited CanBeDismantled flag) until the parent call exists
        rp = pin_in(rets[0], result_pin_name)
        if rp is not None and not list(PL.list_connected_pins(rp)):
            v = ed.add_get_member_variable_node("CanBeDismantled")
            if v is not None: connect(out(v), rp, "interim: inherited CanBeDismantled -> Return")
        print(f"   GUI STEP NEEDED: in {fname}, right-click the purple entry node -> 'Add call to parent function', Compile, Save; then re-run")
        return ed
    if len(parent) == 1 and not list(PL.list_connected_pins(exec_in(parent[0]))):
        PL.break_pin_links(ed.find_graph_entry_pin()); connect(ed.find_graph_entry_pin(), exec_in(parent[0]), "entry -> Parent")
        for p in [q for q in lib.list_output_pins(entry) if str(PL.get_pin_name(q)) != "then"]:
            tgt = next((q for q in lib.list_input_pins(parent[0]) if str(PL.get_pin_name(q)) == str(PL.get_pin_name(p))), None)
            if tgt is not None: connect(p, tgt, f"{PL.get_pin_name(p)} -> Parent")
        connect(then_out(parent[0]), exec_in(rets[0]), "Parent -> Return")
    ret, parent = rets[0], parent[0]
    print("   return pins:", pins(ret), "| parent pins:", pins(parent))
    res_in = pin_in(ret, result_pin_name)
    parent_res = next((p for p in lib.list_output_pins(parent) if str(PL.get_pin_name(p)) == result_pin_name), None)
    check(res_in is not None and parent_res is not None, f"result pin {result_pin_name!r} on both")
    # insert our checks on the exec line between Parent and Return
    PL.break_pin_links(exec_in(ret))
    gpr = call(ed, f"{BPL_C}:GetPawnRank", "GetPawnRank"); connect(char, pin_in(gpr, "Pawn"), "character -> GetPawnRank"); connect(then_out(parent), exec_in(gpr), "Parent -> GetPawnRank")
    igm = call(ed, f"{BPL_C}:IsGuildMemberRank", "IsGuildMemberRank"); connect(out(gpr, "Rank"), pin_in(igm, "Rank"), "rank"); connect(then_out(gpr), exec_in(igm), "-> member")
    req = ed.add_get_member_variable_node("RequiredRank")
    mrr = call(ed, f"{BPL_C}:MeetsRankRequirement", "MeetsRankRequirement"); connect(out(gpr, "Rank"), pin_in(mrr, "Rank"), "rank"); connect(out(req), pin_in(mrr, "Required"), "required"); connect(then_out(igm), exec_in(mrr), "-> meets")
    cast_names = available(ed, [char], "Cast", "ConanCharacter")
    if cast_names:
        cc = create_by_search(ed, [char], ("Cast", "ConanCharacter"), "Cast To ConanCharacter", exact="Utilities|Casting|CastToConanCharacter")
        connect(char, pin_in(cc, "Object"), "character -> cast"); connect(then_out(mrr), exec_in(cc), "-> cast"); char_pin = as_pin(cc); tail = then_out(cc); cast_failed = lib.find_output_pin(cc, "CastFailed")
    else:
        print("   (parameter is already a ConanCharacter - no cast needed)"); char_pin = char; tail = then_out(mrr); cast_failed = None
    gid = call(ed, "/Script/ConanSandbox.ConanCharacter:GetGuildStableId", "GetGuildStableId"); connect(char_pin, lib.find_self_pin(gid) or pin_in(gid, "self"), "char -> GetGuildStableId")
    if has_exec(gid): connect(tail, exec_in(gid), "-> GetGuildStableId"); tail = then_out(gid)
    conv = call(ed, unreal.StableIdFunctionLibrary.static_class().get_path_name() + ":Conv_StableIdToString", "StableId->String"); connect(out(gid, "ReturnValue"), lib.list_input_pins(conv)[0], "stable id -> string")
    if has_exec(conv): connect(tail, exec_in(conv), "-> Conv"); tail = then_out(conv)
    gc = call(ed, f"{BPL_C}:GetGAController", "GetGAController"); connect(tail, exec_in(gc), "-> GetGAController")
    isa = call(ed, f"{MOD_C}:IsAllowed", "IsAllowed"); connect(out(gc, "Controller"), lib.find_self_pin(isa) or pin_in(isa, "self"), "ctrl"); connect(out(conv, "ReturnValue"), pin_in(isa, "GuildId"), "g")
    setval(isa, "Perm", str(perm)); connect(out(gpr, "Rank"), pin_in(isa, "Rank"), "rank"); connect(then_out(gc), exec_in(isa), "-> IsAllowed")
    # allowed_by_mod = NOT member OR (meets AND IsAllowed)
    a1 = call(ed, M + "BooleanAND", "AND"); connect(out(mrr, "Result"), pin_in(a1, "A"), "meets"); connect(out(isa, "Allowed"), pin_in(a1, "B"), "allowed")
    notm = call(ed, M + "Not_PreBool", "NOT"); connect(out(igm, "Result"), pin_in(notm, "A"), "member")
    o1 = call(ed, M + "BooleanOR", "OR"); connect(out(notm, "ReturnValue"), pin_in(o1, "A"), "not member"); connect(out(a1, "ReturnValue"), pin_in(o1, "B"), "meets&allowed")
    a2 = call(ed, M + "BooleanAND", "AND parent"); connect(parent_res, pin_in(a2, "A"), "parent"); connect(out(o1, "ReturnValue"), pin_in(a2, "B"), "ours")
    # the cast can fail (NPCs): CastFailed -> Return with the parent's verdict
    PL.break_pin_links(res_in); connect(out(a2, "ReturnValue"), res_in, "AND -> Return")
    connect(then_out(isa), exec_in(ret), "IsAllowed -> Return")
    if cast_failed is not None:
        ret2 = ed.add_return_node(); connect(cast_failed, exec_in(ret2), "CastFailed -> Return(parent)"); connect(parent_res, pin_in(ret2, result_pin_name), "parent -> Return2")
    return ed

e1 = gate("GetCanBeDismantled", 0, "CanBeDismantled")
# pick-up (perm 1): the overridable CanReturnToInventory has no character parameter (the C++ signature wins over
# Master's Blueprint one), so it cannot be gated per player here. Recorded as a known gap in the v2 plan.
compile_ok(bp, [(e1, "GetCanBeDismantled")], TARGET)
if MODE == "real" and not failures: save(bp, DISK, TARGET)
elif MODE == "real": print("   NOT SAVING: failures above")
result()
