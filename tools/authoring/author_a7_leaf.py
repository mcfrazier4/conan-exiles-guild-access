"""A7 - move the feature off BP_Master_Placeables onto the leaf classes so a mod
that overrides Master (LBPR does) no longer breaks us. Run WITH -ModDevKit.
GA_MODE=dry|real. GA_TARGET=container|door. Idempotent.

Per target class:
  1. class-local RequiredRank (Byte, RepNotify; SaveGame is a GUI tick)
  2. every existing 'Get RequiredRank' node (pointing at Master's variable) retargeted to the local one
  3. SCS GuildAccessLock (BPC_GA_Lock)
  4. server handler on OnComponentActivated
  5. rank submenu appended to InteractableMenu (parent chain kept)
  6. hover text; container also: ShouldDisableInteraction override with the rank-aware denial text
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

TARGET = os.environ.get("GA_TARGET", "container").lower()
CLASSES = {
    "container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
    "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset"),
}
PATH, REL = CLASSES[TARGET]
DISK = os.path.join(DISK_CONTENT, REL)
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
LOCK_C = f"{LOCAL}/BPC_GA_Lock.BPC_GA_Lock_C"
PLAYER_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
BADGES = ["T_Rank_Recruit", "T_Rank_Member", "T_Rank_Officer", "T_Rank_GuildMaster"]
LOCK_ICON = "/Game/UI/Textures/GUIs/MainRadialMenu/MainRadialMenuIconLocked.MainRadialMenuIconLocked"
RANKS = [("Recruit", "Everyone in the clan"), ("Member", "Members and above"), ("Officer", "Officers and the guild master"), ("Guild Master", "Guild master only")]
byte_t = lib.get_basic_type_by_name("byte")

sec(f"mode = {MODE}  target = {TARGET} ({PATH})")
wait_registry()
bp = unreal.load_asset(PATH); check(bp is not None, "loaded target override")
lock_cls = unreal.load_class(None, LOCK_C); check(lock_cls is not None, "Lock class")
ed = GE.get_graph_editor_by_name(bp, "EventGraph"); check(ed is not None, "EventGraph")

def bpl_call(g, fn): return call(g, f"{BPL_C}:{fn}", fn)
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def rank_text(g, rank_pin):
    rt = bpl_call(g, "RankToText"); connect(rank_pin, lib.find_input_pin(rt, "Rank"), "rank -> RankToText"); return out(rt, "Result")
def str_text(g, prefix, text_pin):
    t2s = call(g, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "TextToString"); connect(text_pin, lib.find_input_pin(t2s, "InText"), "-> ToString")
    cc = call(g, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat"); setval(cc, "A", prefix); connect(out(t2s, "ReturnValue"), lib.find_input_pin(cc, "B"), "-> Concat.B")
    s2t = call(g, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "StringToText"); connect(out(cc, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "-> ToText")
    return out(s2t, "ReturnValue")
def cast_pc(g, obj_pin):
    c = create_by_search(g, [obj_pin], ("Cast", "ConanPlayerController"), "Cast To ConanPlayerController", exact="Utilities|Casting|CastToConanPlayerController")
    connect(obj_pin, lib.find_input_pin(c, "Object"), "-> Cast.Object"); return c
def notify(g, pc_pin, text_pin, positive):
    n = call(g, "/Script/ConanSandbox.ConanPlayerController:ClientHUDShowNotification", "notify")
    connect(pc_pin, lib.find_self_pin(n) or lib.find_input_pin(n, "self"), "PC -> notify.self"); connect(text_pin, lib.find_input_pin(n, "text"), "text -> notify"); setval(n, "positive", positive); return n
def insert_sequence_after(g, exec_out_pin, label):
    """Put a Sequence between exec_out_pin and whatever it fed; return the free then_1 pin."""
    old = list(PL.list_connected_pins(exec_out_pin))
    seq = create_by_search(g, [], ("FlowControl", "Sequence"), f"Sequence ({label})", exact="Utilities|FlowControl|Sequence")
    PL.break_pin_links(exec_out_pin)
    connect(exec_out_pin, exec_in(seq), f"{label} -> Sequence")
    if old: connect(lib.find_output_pin(seq, "then_0"), old[0], "Sequence.then_0 -> original chain")
    return lib.find_output_pin(seq, "then_1")

# ---------------------------------------------------------------- 1. local variable
sec("1. class-local RequiredRank")
if "RequiredRank" in [str(v) for v in lib.list_member_variable_names(bp)]: print("   exists")
else:
    check(lib.add_member_variable(bp, "RequiredRank", byte_t), "add RequiredRank")
    lib.set_blueprint_variable_replication(bp, "RequiredRank", unreal.BlueprintVariableReplication.REP_NOTIFY)
    check("REP_NOTIFY" in str(lib.get_blueprint_variable_replication(bp, "RequiredRank")), "RepNotify")
check(lib.compile_blueprint(bp), "compile after variable")

# ---------------------------------------------------------------- 2. retarget Get RequiredRank nodes
sec("2. retarget existing 'Get RequiredRank' getters to the local variable")
for g in [str(x) for x in lib.list_graph_names(bp)]:
    e = GE.get_graph_editor_by_name(bp, g)
    if not e: continue
    for n in [n for n in e.list_all_nodes() if n.get_class().get_name() == "K2Node_VariableGet" and title(n) == "Get RequiredRank"]:
        links = list(PL.list_connected_pins(out(n)))
        new = e.add_get_member_variable_node("RequiredRank")
        ok = new is not None
        for l in links: ok = connect(out(new), l, f"[{g}] local RequiredRank -> {title(PL.get_owning_node(l))}.{PL.get_pin_name(l)}") and ok
        e.remove_nodes([n]); check(ok, f"[{g}] getter retargeted ({len(links)} links)")

# ---------------------------------------------------------------- 3. SCS lock component
sec("3. SCS GuildAccessLock")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
lock_template = None; root = None
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    d = sds.k2_find_subobject_data_from_handle(h); obj = SDL.get_object(d)
    if root is None and obj is not None and isinstance(obj, unreal.Actor): root = h
    if obj is not None and obj.get_class().get_path_name() == LOCK_C: lock_template = obj; print("   existing:", obj.get_name())
if lock_template is None:
    res = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=lock_cls, blueprint_context=bp))
    nh = res[0] if isinstance(res, (tuple, list)) else res
    d = sds.k2_find_subobject_data_from_handle(nh) if nh else None; lock_template = SDL.get_object(d) if d else None
    check(lock_template is not None, "added SCS lock component")
    if lock_template: sds.rename_subobject(nh, unreal.Text("GuildAccessLock"))
check(lib.compile_blueprint(bp), "compile after SCS")

# ---------------------------------------------------------------- 4. server handler
sec("4. server handler OnComponentActivated")
if [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_ComponentBoundEvent"]: print("   exists")
elif lock_template is not None:
    bev = ed.add_component_bound_event_node(lock_template, "OnComponentActivated"); check(bev is not None, "bound event")
    ha = call(ed, "/Script/Engine.Actor:HasAuthority", "HasAuthority"); br_auth = ed.add_branch_node()
    connect(then_out(bev), exec_in(br_auth), "event -> Branch(auth)"); connect(out(ha, "ReturnValue"), lib.find_condition_pin(br_auth), "auth -> cond")
    gl = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Lock)"); setval(gl, "ComponentClass", LOCK_C); lock_pin = out(gl, "ReturnValue")
    inst = ed.add_get_member_variable_node("PendingInstigator", LOCK_C); connect(lock_pin, lib.find_self_pin(inst) or lib.find_input_pin(inst, "self"), "lock -> Get PendingInstigator")
    newr = ed.add_get_member_variable_node("PendingRank", LOCK_C); connect(lock_pin, lib.find_self_pin(newr) or lib.find_input_pin(newr, "self"), "lock -> Get PendingRank")
    inst_pin, newr_pin = out(inst, "PendingInstigator"), out(newr, "PendingRank")
    gp = call(ed, "/Script/Engine.Controller:K2_GetPawn", "GetPawn"); connect(inst_pin, lib.find_self_pin(gp) or lib.find_input_pin(gp, "self"), "inst -> GetPawn"); pawn = out(gp, "ReturnValue")
    gpr = bpl_call(ed, "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank"); connect(then_out(br_auth), exec_in(gpr), "auth.then -> GetPawnRank")
    cast = cast_pc(ed, inst_pin); connect(then_out(gpr), exec_in(cast), "GetPawnRank -> Cast"); pc_pin = as_pin(cast)
    isown = call(ed, "/Script/ConanSandbox.BuildableBase:IsOwner", "IsOwner"); connect(pawn, lib.find_input_pin(isown, "Pawn"), "pawn -> IsOwner"); setval(isown, "bSendGuiNotification", "false")
    req = ed.add_get_member_variable_node("RequiredRank")
    can = bpl_call(ed, "RankCanSetRequired"); connect(out(gpr, "Rank"), lib.find_input_pin(can, "Rank"), "rank -> CanSet"); connect(out(req), lib.find_input_pin(can, "CurrentRequired"), "Required -> CanSet")
    andn = call(ed, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND"); connect(out(isown, "ReturnValue"), lib.find_input_pin(andn, "A"), "IsOwner -> AND"); connect(out(can, "Result"), lib.find_input_pin(andn, "B"), "CanSet -> AND")
    br_perm = ed.add_branch_node(); connect(then_out(cast), exec_in(br_perm), "Cast -> Branch(perm)"); connect(out(andn, "ReturnValue"), lib.find_condition_pin(br_perm), "AND -> cond")
    le = call(ed, "/Script/Engine.KismetMathLibrary:LessEqual_ByteByte", "<=3"); connect(newr_pin, lib.find_input_pin(le, "A"), "NewRank -> <="); setval(le, "B", "3")
    br_valid = ed.add_branch_node(); connect(then_out(br_perm), exec_in(br_valid), "perm.then -> Branch(valid)"); connect(out(le, "ReturnValue"), lib.find_condition_pin(br_valid), "<=3 -> cond")
    setr = ed.add_set_member_variable_node("RequiredRank"); connect(newr_pin, lib.find_input_pin(setr, "RequiredRank"), "NewRank -> Set"); connect(then_out(br_valid), exec_in(setr), "valid -> Set")
    pers = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(ActorPersistence)"); setval(pers, "ComponentClass", unreal.ActorPersistenceComponent.static_class().get_path_name())
    sd = create_by_search(ed, [out(pers, "ReturnValue")], ("SetDirty",), "SetDirty")
    tail = then_out(setr)
    if sd is not None:
        sp = lib.find_self_pin(sd) or lib.find_input_pin(sd, "self")
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(pers, "ReturnValue"), sp, "pers -> SetDirty.self")
        setval(sd, "bDirty", "true"); connect(then_out(setr), exec_in(sd), "Set -> SetDirty"); tail = then_out(sd)
    ok = notify(ed, pc_pin, str_text(ed, "Access rank set to ", rank_text(ed, newr_pin)), "true"); connect(tail, exec_in(ok), "-> notify ok")
    deny = call(ed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "deny text"); setval(deny, "InString", "You cannot change this access rank")
    no = notify(ed, pc_pin, out(deny, "ReturnValue"), "false"); connect(lib.find_else_pin(br_perm), exec_in(no), "perm.else -> notify denied")

# ---------------------------------------------------------------- 5. menu
sec("5. InteractableMenu rank submenu")
menu_ready = False
if any("SetAccessRank" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "") for n in nodes_titled(ed, "AddItem") if lib.find_input_pin(n, "label")):
    print("   exists")
else:
    evs = nodes_titled(ed, "Event InteractableMenu")
    menu_ready = True
    if evs and list(PL.list_connected_pins(then_out(evs[0]))):
        ev = evs[0]; tail = insert_sequence_after(ed, then_out(ev), "InteractableMenu")
    else:
        ev = evs[0] if evs else lib.add_event_override(bp, "InteractableMenu", unreal.IntPoint(0, 0)); check(ev is not None, "Event InteractableMenu node")
        parents = nodes_titled(ed, "Parent: InteractableMenu")
        if parents:
            parent = parents[0]
            connect(out(ev, "RadialMenu"), lib.find_input_pin(parent, "RadialMenu"), "RadialMenu -> Parent"); connect(out(ev, "HitIndex"), lib.find_input_pin(parent, "HitIndex"), "HitIndex -> Parent")
            connect(then_out(ev), exec_in(parent), "event -> Parent"); tail = then_out(parent)
        else:
            menu_ready = False
            print("   GUI STEP NEEDED: right-click 'Event InteractableMenu' -> 'Add call to parent function', Compile, Save; then re-run this script")
    radial = out(ev, "RadialMenu")
if not any("SetAccessRank" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "") for n in nodes_titled(ed, "AddItem") if lib.find_input_pin(n, "label")) and menu_ready:
    gopp = call(ed, "/Script/UMG.UserWidget:GetOwningPlayerPawn", "GetOwningPlayerPawn"); connect(radial, lib.find_self_pin(gopp) or lib.find_input_pin(gopp, "self"), "RadialMenu -> GetOwningPlayerPawn"); pawn = out(gopp, "ReturnValue")
    isown = call(ed, "/Script/ConanSandbox.BuildableBase:IsOwner", "IsOwner (menu)"); connect(pawn, lib.find_input_pin(isown, "Pawn"), "pawn -> IsOwner"); setval(isown, "bSendGuiNotification", "false")
    gpr = bpl_call(ed, "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank"); connect(tail, exec_in(gpr), "-> GetPawnRank")
    req = ed.add_get_member_variable_node("RequiredRank")
    can = bpl_call(ed, "RankCanSetRequired"); connect(out(gpr, "Rank"), lib.find_input_pin(can, "Rank"), "rank -> CanSet"); connect(out(req), lib.find_input_pin(can, "CurrentRequired"), "Required -> CanSet")
    andn = call(ed, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND"); connect(out(isown, "ReturnValue"), lib.find_input_pin(andn, "A"), "IsOwner -> AND"); connect(out(can, "Result"), lib.find_input_pin(andn, "B"), "CanSet -> AND")
    br = ed.add_branch_node(); connect(then_out(gpr), exec_in(br), "GetPawnRank -> Branch"); connect(out(andn, "ReturnValue"), lib.find_condition_pin(br), "AND -> cond")
    add = call(ed, "/Script/ConanSandbox.RadialMenu:AddItem", "AddItem"); connect(radial, lib.find_self_pin(add) or lib.find_input_pin(add, "self"), "RadialMenu -> AddItem")
    setval(add, "label", text_lit("SetAccessRank", "Set Access Rank")); setval(add, "icon", LOCK_ICON)
    connect(str_text(ed, "Current: ", rank_text(ed, out(req))), lib.find_input_pin(add, "subtitle"), "subtitle"); connect(then_out(br), exec_in(add), "Branch -> AddItem")
    entry = out(add, "ReturnValue"); tail = then_out(add)
    selfn = create_by_search(ed, [], ("Getareferencetoself",), "Self", exact="Variables|Getareferencetoself"); self_pin = out(selfn)
    for i, (name, desc) in enumerate(RANKS):
        sub = call(ed, "/Script/ConanSandbox.RadialMenuEntry:AddSubItem", f"AddSubItem {name}"); connect(entry, lib.find_self_pin(sub) or lib.find_input_pin(sub, "self"), f"entry -> sub[{i}]")
        setval(sub, "label", text_lit(f"Rank{i}Label", name)); setval(sub, "subtitle", text_lit(f"Rank{i}Desc", desc)); setval(sub, "icon", f"/Game/UI/Textures/GUIs/Guild/{BADGES[i]}.{BADGES[i]}")
        connect(tail, exec_in(sub), f"-> sub[{i}]")
        lib.compile_blueprint(bp)
        before = snapshot(ed)
        asg = create_by_search(ed, [out(sub, "ReturnValue")], ("Assign", "SignalClicked"), f"Assign [{i}]", exact="Menu|Event|AssignSignalClicked")
        cev = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(cev) == 1, f"click event [{i}]")
        sp = lib.find_self_pin(asg) or lib.find_input_pin(asg, "self")
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(sub, "ReturnValue"), sp, f"sub -> Assign[{i}].self")
        connect(then_out(sub), exec_in(asg), f"sub[{i}] -> Assign"); tail = then_out(asg)
        if cev:
            pc0 = call(ed, "/Script/Engine.GameplayStatics:GetPlayerController", "GetPlayerController(0)")
            gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(out(pc0, "ReturnValue"), lib.find_input_pin(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PLAYER_C)
            rpc = call(ed, f"{PLAYER_C}:Server_ServerSetRequiredRank_0", "RPC"); connect(out(gcb, "ReturnValue"), lib.find_self_pin(rpc) or lib.find_input_pin(rpc, "self"), "component -> RPC.self")
            connect(self_pin, lib.find_input_pin(rpc, "Target"), "self -> Target"); setval(rpc, "NewRank", str(i)); connect(then_out(cev[0]), exec_in(rpc), f"click[{i}] -> RPC")

# ---------------------------------------------------------------- 6. hover text
sec("6. hover text (InteractableGetSimpleDisplayText)")
hed = GE.get_graph_editor_by_name(bp, "InteractableGetSimpleDisplayText")
if hed is None:
    g = lib.add_function_override(bp, "InteractableGetSimpleDisplayText"); hed = GE.get_graph_editor(g) if g else None
    check(hed is not None, "function override created")
if hed is not None and any(n.get_class().get_name() == "K2Node_IfThenElse" for n in hed.list_all_nodes()): print("   exists")
elif hed is not None:
    entry_pin = hed.find_graph_entry_pin(); first = list(PL.list_connected_pins(entry_pin))
    PL.break_pin_links(entry_pin)
    req = hed.add_get_member_variable_node("RequiredRank")
    gt = call(hed, "/Script/Engine.KismetMathLibrary:Greater_ByteByte", ">0"); connect(out(req), lib.find_input_pin(gt, "A"), "Required -> >"); setval(gt, "B", "0")
    br = hed.add_branch_node(); connect(entry_pin, exec_in(br), "entry -> Branch"); connect(out(gt, "ReturnValue"), lib.find_condition_pin(br), "> -> cond")
    if first: connect(lib.find_else_pin(br), first[0], "else -> original chain")
    ret1 = hed.add_return_node(); connect(then_out(br), exec_in(ret1), "then -> Return(text)")
    gbn = call(hed, "/Script/ConanSandbox.BuildableBase:GetBuildableName", "GetBuildableName"); setval(gbn, "ignoreCustomName", "false")
    n2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "name ToString"); connect(out(gbn, "ReturnValue"), lib.find_input_pin(n2s, "InText"), "name -> ToString")
    r2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "rank ToString"); connect(rank_text(hed, out(req)), lib.find_input_pin(r2s, "InText"), "rank -> ToString")
    c1 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "c1"); setval(c1, "A", " - Requires "); connect(out(r2s, "ReturnValue"), lib.find_input_pin(c1, "B"), "rank -> c1")
    c2 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "c2"); connect(out(n2s, "ReturnValue"), lib.find_input_pin(c2, "A"), "name -> c2"); connect(out(c1, "ReturnValue"), lib.find_input_pin(c2, "B"), "c1 -> c2")
    s2t = call(hed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "ToText"); connect(out(c2, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "c2 -> ToText")
    connect(out(s2t, "ReturnValue"), lib.find_input_pin(ret1, "ReturnValue"), "text -> Return")

# ---------------------------------------------------------------- 7. container denial text
graphs_to_check = [(ed, "EventGraph"), (hed, "InteractableGetSimpleDisplayText")]
if TARGET == "container":
    sec("7. ShouldDisableInteraction override: rank-aware 'Container is locked - requires <rank>'")
    sed = GE.get_graph_editor_by_name(bp, "ShouldDisableInteraction")
    if sed is None:
        g = lib.add_function_override(bp, "ShouldDisableInteraction"); sed = GE.get_graph_editor(g) if g else None
        check(sed is not None, "function override created")
    if sed is not None and nodes_titled(sed, "MeetsRankRequirement"): print("   exists")
    elif sed is not None:
        entry = [n for n in sed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionEntry"][0]
        params = [p for p in lib.list_output_pins(entry) if str(PL.get_pin_name(p)) != "then"]
        print("   entry params:", [str(PL.get_pin_name(p)) for p in params])
        pawn = next((p for p in params if "Character" in str(PL.get_pin_name(p)) or "Pawn" in str(PL.get_pin_name(p))), None)
        check(pawn is not None, "found the pawn parameter")
        entry_pin = sed.find_graph_entry_pin(); first = list(PL.list_connected_pins(entry_pin)); PL.break_pin_links(entry_pin)
        gpr = bpl_call(sed, "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank"); connect(entry_pin, exec_in(gpr), "entry -> GetPawnRank")
        igm = bpl_call(sed, "IsGuildMemberRank"); connect(out(gpr, "Rank"), lib.find_input_pin(igm, "Rank"), "rank -> member"); connect(then_out(gpr), exec_in(igm), "-> member")
        req = sed.add_get_member_variable_node("RequiredRank")
        mrr = bpl_call(sed, "MeetsRankRequirement"); connect(out(gpr, "Rank"), lib.find_input_pin(mrr, "Rank"), "rank -> meets"); connect(out(req), lib.find_input_pin(mrr, "Required"), "Required -> meets"); connect(then_out(igm), exec_in(mrr), "-> meets")
        notn = call(sed, "/Script/Engine.KismetMathLibrary:Not_PreBool", "NOT"); connect(out(mrr, "Result"), lib.find_input_pin(notn, "A"), "meets -> NOT")
        andn = call(sed, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND"); connect(out(igm, "Result"), lib.find_input_pin(andn, "A"), "member -> AND"); connect(out(notn, "ReturnValue"), lib.find_input_pin(andn, "B"), "NOT -> AND")
        br = sed.add_branch_node(); connect(then_out(mrr), exec_in(br), "meets -> Branch"); connect(out(andn, "ReturnValue"), lib.find_condition_pin(br), "rank-denied -> cond")
        if first: connect(lib.find_else_pin(br), first[0], "else -> original (Parent) chain")
        gc = call(sed, "/Script/Engine.Pawn:GetController", "GetController"); connect(pawn, lib.find_self_pin(gc) or lib.find_input_pin(gc, "self"), "pawn -> GetController")
        cast = cast_pc(sed, out(gc, "ReturnValue")); connect(then_out(br), exec_in(cast), "denied -> Cast")
        no = notify(sed, as_pin(cast), str_text(sed, "Container is locked - requires ", rank_text(sed, out(req))), "false"); connect(then_out(cast), exec_in(no), "Cast -> notify")
        ret = sed.add_return_node(); connect(then_out(no), exec_in(ret), "notify -> Return(true)")
        rv = lib.find_input_pin(ret, "ReturnValue")
        if rv is not None: setval(ret, "ReturnValue", "true")
        else:
            outs = [str(PL.get_pin_name(p)) for p in lib.list_input_pins(ret)]; print("   return pins:", outs)
            for pn in outs:
                if pn != "execute": setval(ret, pn, "true"); break
    if sed is not None: graphs_to_check.append((sed, "ShouldDisableInteraction"))

sec("compile")
compile_ok(bp, graphs_to_check, TARGET)
if MODE == "real" and not failures: save(bp, DISK, TARGET)
elif MODE == "real": print("   NOT SAVING: failures above")
result()
