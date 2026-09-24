"""A5 - hinged building doors (BP_BuildDoor, T2/T3). Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

Same feature set as BP_Master_Placeables, on the BP_BuildingBase family:
  RequiredRank (Byte, RepNotify; SaveGame is a GUI tick), SCS GuildAccessLock (BPC_GA_Lock),
  server handler on OnComponentActivated, InteractableMenu with the rank submenu,
  gate in InteractableActivate with 'Door is locked - requires <rank>', hover text.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

DOOR = "/Game/Systems/Building/BP_BuildDoor"
DOOR_DISK = os.path.join(DISK_CONTENT, r"Systems\Building\BP_BuildDoor.uasset")
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
LOCK_C = f"{LOCAL}/BPC_GA_Lock.BPC_GA_Lock_C"
PLAYER_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
LOCK_ICON = "/Game/UI/Textures/GUIs/MainRadialMenu/MainRadialMenuIconLocked.MainRadialMenuIconLocked"
RANKS = [("Recruit", "Everyone in the clan"), ("Member", "Members and above"), ("Officer", "Officers and the guild master"), ("Guild Master", "Guild master only")]
byte_t = lib.get_basic_type_by_name("byte")

sec(f"mode = {MODE}")
wait_registry()
door = unreal.load_asset(DOOR); check(door is not None, "loaded BP_BuildDoor")
lock_cls = unreal.load_class(None, LOCK_C); check(lock_cls is not None, "Lock class")
ed = GE.get_graph_editor_by_name(door, "EventGraph"); check(ed is not None, "EventGraph")

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
def gcb_lock(g):
    n = call(g, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Lock)"); setval(n, "ComponentClass", LOCK_C); return out(n, "ReturnValue")
def cast_pc(g, obj_pin):
    c = create_by_search(g, [obj_pin], ("Cast", "ConanPlayerController"), "Cast To ConanPlayerController", exact="Utilities|Casting|CastToConanPlayerController")
    connect(obj_pin, lib.find_input_pin(c, "Object"), "-> Cast.Object"); return c
def notify(g, pc_pin, text_pin, positive):
    n = call(g, "/Script/ConanSandbox.ConanPlayerController:ClientHUDShowNotification", "notify")
    connect(pc_pin, lib.find_self_pin(n) or lib.find_input_pin(n, "self"), "PC -> notify.self"); connect(text_pin, lib.find_input_pin(n, "text"), "text -> notify"); setval(n, "positive", positive); return n

# ---------------------------------------------------------------- 1. variable
sec("1. RequiredRank variable")
if "RequiredRank" in [str(v) for v in lib.list_member_variable_names(door)]: print("   exists")
else:
    check(lib.add_member_variable(door, "RequiredRank", byte_t), "add RequiredRank")
    lib.set_blueprint_variable_replication(door, "RequiredRank", unreal.BlueprintVariableReplication.REP_NOTIFY)
    check("REP_NOTIFY" in str(lib.get_blueprint_variable_replication(door, "RequiredRank")), "RequiredRank RepNotify")
check(lib.compile_blueprint(door), "compile after variable")

# ---------------------------------------------------------------- 2. SCS lock component
sec("2. SCS component GuildAccessLock")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem); SDL = unreal.SubobjectDataBlueprintFunctionLibrary
lock_template = None; root = None
for h in sds.k2_gather_subobject_data_for_blueprint(door):
    d = sds.k2_find_subobject_data_from_handle(h); obj = SDL.get_object(d)
    if root is None and obj is not None and isinstance(obj, unreal.Actor): root = h
    if obj is not None and obj.get_class().get_path_name() == LOCK_C: lock_template = obj; print("   existing:", obj.get_name())
if lock_template is None:
    check(root is not None, "root handle")
    res = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=lock_cls, blueprint_context=door))
    nh = res[0] if isinstance(res, (tuple, list)) else res
    d = sds.k2_find_subobject_data_from_handle(nh) if nh else None; lock_template = SDL.get_object(d) if d else None
    check(lock_template is not None, "added SCS lock component")
    if lock_template: sds.rename_subobject(nh, unreal.Text("GuildAccessLock"))
check(lib.compile_blueprint(door), "compile after SCS")

# ---------------------------------------------------------------- 3. server handler
sec("3. server handler OnComponentActivated")
if [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_ComponentBoundEvent"]: print("   exists")
elif lock_template is not None:
    bev = ed.add_component_bound_event_node(lock_template, "OnComponentActivated"); check(bev is not None, "bound event")
    ha = call(ed, "/Script/Engine.Actor:HasAuthority", "HasAuthority"); br_auth = ed.add_branch_node()
    connect(then_out(bev), exec_in(br_auth), "event -> Branch(auth)"); connect(out(ha, "ReturnValue"), lib.find_condition_pin(br_auth), "auth -> cond")
    lock_pin = gcb_lock(ed)
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
    # persistence: whichever persistence component this building has
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

# ---------------------------------------------------------------- 4. menu (new InteractableMenu event)
sec("4. InteractableMenu")
if nodes_titled(ed, "Event InteractableMenu"): print("   exists")
else:
    ev = lib.add_event_override(door, "InteractableMenu", unreal.IntPoint(0, 0)); check(ev is not None, f"add_event_override InteractableMenu -> {pins(ev) if ev else None}")
    radial = out(ev, "RadialMenu")
    parent = create_by_search(ed, [], ("Parent", "InteractableMenu"), "Parent: InteractableMenu") if available(ed, [], "Parent", "InteractableMenu") else None
    if parent is None: print("   (no parent InteractableMenu implementation to chain - vanilla BP_BuildDoor has none)")
    tail = then_out(ev)
    if parent is not None:
        connect(radial, lib.find_input_pin(parent, "RadialMenu"), "RadialMenu -> Parent"); connect(out(ev, "HitIndex"), lib.find_input_pin(parent, "HitIndex"), "HitIndex -> Parent")
        connect(tail, exec_in(parent), "event -> Parent"); tail = then_out(parent)
    gopp = call(ed, "/Script/UMG.UserWidget:GetOwningPlayerPawn", "GetOwningPlayerPawn"); connect(radial, lib.find_self_pin(gopp) or lib.find_input_pin(gopp, "self"), "RadialMenu -> GetOwningPlayerPawn")
    pawn = out(gopp, "ReturnValue")
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
        setval(sub, "label", text_lit(f"Rank{i}Label", name)); setval(sub, "subtitle", text_lit(f"Rank{i}Desc", desc)); setval(sub, "icon", LOCK_ICON)
        connect(tail, exec_in(sub), f"-> sub[{i}]")
        lib.compile_blueprint(door)
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

# ---------------------------------------------------------------- 5. gate in InteractableActivate
sec("5. gate InteractableActivate")
ev = nodes_titled(ed, "Event InteractableActivate"); check(len(ev) == 1, "Event InteractableActivate"); ev = ev[0]
gate_done = any(title(n) == "MeetsRankRequirement" for n in ed.list_all_nodes())
if gate_done: print("   exists")
else:
    own_br = [PL.get_owning_node(c) for c in PL.list_connected_pins(then_out(ev))]; check(len(own_br) == 1 and own_br[0].get_class().get_name() == "K2Node_IfThenElse", "event -> IsOwner Branch"); own_br = own_br[0]
    nxt = list(PL.list_connected_pins(then_out(own_br))); check(len(nxt) == 1, "IsOwner.then -> open Branch"); open_exec = nxt[0]
    pawn = list(PL.list_connected_pins(lib.find_input_pin(nodes_titled(ed, "IsOwner")[0], "Pawn")))[0]
    PL.break_pin_links(then_out(own_br))
    gpr = bpl_call(ed, "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank (gate)"); connect(then_out(own_br), exec_in(gpr), "IsOwner.then -> GetPawnRank")
    igm = bpl_call(ed, "IsGuildMemberRank"); connect(out(gpr, "Rank"), lib.find_input_pin(igm, "Rank"), "rank -> member"); connect(then_out(gpr), exec_in(igm), "-> member")
    req = ed.add_get_member_variable_node("RequiredRank")
    mrr = bpl_call(ed, "MeetsRankRequirement"); connect(out(gpr, "Rank"), lib.find_input_pin(mrr, "Rank"), "rank -> meets"); connect(out(req), lib.find_input_pin(mrr, "Required"), "Required -> meets"); connect(then_out(igm), exec_in(mrr), "-> meets")
    notn = call(ed, "/Script/Engine.KismetMathLibrary:Not_PreBool", "NOT"); connect(out(igm, "Result"), lib.find_input_pin(notn, "A"), "member -> NOT")
    orn = call(ed, "/Script/Engine.KismetMathLibrary:BooleanOR", "OR"); connect(out(notn, "ReturnValue"), lib.find_input_pin(orn, "A"), "NOT -> OR"); connect(out(mrr, "Result"), lib.find_input_pin(orn, "B"), "meets -> OR")
    gate = ed.add_branch_node(); connect(then_out(mrr), exec_in(gate), "meets -> gate"); connect(out(orn, "ReturnValue"), lib.find_condition_pin(gate), "OR -> gate.cond")
    connect(then_out(gate), open_exec, "gate.then -> original open Branch")
    cast = cast_pc(ed, out(ev, "Instigator")); connect(lib.find_else_pin(gate), exec_in(cast), "gate.else -> Cast")
    no = notify(ed, as_pin(cast), str_text(ed, "Door is locked - requires ", rank_text(ed, out(req))), "false"); connect(then_out(cast), exec_in(no), "Cast -> notify")

# ---------------------------------------------------------------- 6. hover text
sec("6. hover text")
hed = GE.get_graph_editor_by_name(door, "InteractableGetSimpleDisplayText")
if any(n.get_class().get_name() == "K2Node_IfThenElse" for n in hed.list_all_nodes()): print("   exists")
else:
    entry_pin = hed.find_graph_entry_pin(); ret0 = [n for n in hed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"][0]
    PL.break_pin_links(entry_pin)
    req = hed.add_get_member_variable_node("RequiredRank")
    gt = call(hed, "/Script/Engine.KismetMathLibrary:Greater_ByteByte", ">0"); connect(out(req), lib.find_input_pin(gt, "A"), "Required -> >"); setval(gt, "B", "0")
    br = hed.add_branch_node(); connect(entry_pin, exec_in(br), "entry -> Branch"); connect(out(gt, "ReturnValue"), lib.find_condition_pin(br), "> -> cond"); connect(lib.find_else_pin(br), exec_in(ret0), "else -> Return")
    ret1 = hed.add_return_node(); connect(then_out(br), exec_in(ret1), "then -> Return(text)")
    gbn = call(hed, "/Script/ConanSandbox.BuildableBase:GetBuildableName", "GetBuildableName"); setval(gbn, "ignoreCustomName", "false")
    n2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "name ToString"); connect(out(gbn, "ReturnValue"), lib.find_input_pin(n2s, "InText"), "name -> ToString")
    r2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "rank ToString"); connect(rank_text(hed, out(req)), lib.find_input_pin(r2s, "InText"), "rank -> ToString")
    c1 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "c1"); setval(c1, "A", " - Requires "); connect(out(r2s, "ReturnValue"), lib.find_input_pin(c1, "B"), "rank -> c1")
    c2 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "c2"); connect(out(n2s, "ReturnValue"), lib.find_input_pin(c2, "A"), "name -> c2"); connect(out(c1, "ReturnValue"), lib.find_input_pin(c2, "B"), "c1 -> c2")
    s2t = call(hed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "ToText"); connect(out(c2, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "c2 -> ToText")
    connect(out(s2t, "ReturnValue"), lib.find_input_pin(ret1, "ReturnValue"), "text -> Return")

sec("compile")
compile_ok(door, [(ed, "EventGraph"), (hed, "InteractableGetSimpleDisplayText")], "BP_BuildDoor")
if MODE == "real" and not failures: save(door, DOOR_DISK, "BP_BuildDoor override")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
