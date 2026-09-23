"""A2 part 2 - BP_Master_Placeables override. Run WITH -ModDevKit. GA_MODE=dry | real. Idempotent.

 1. SCS component  GuildAccessLock : BPC_GA_Lock  (payload carrier; present on every placeable, both sides)
 2. Server handler  OnComponentActivated(GuildAccessLock) -> HasAuthority -> permission -> Set RequiredRank -> SetDirty -> notify
 3. Radial menu     InteractableMenu sequence + "Set Access Rank" (lock icon) with 4 rank sub-items;
                    each click -> local PlayerController.BPC_GA_Player.ServerSetRequiredRank(self, rank)
 4. Hover text      InteractableGetSimpleDisplayText -> "<name> - Requires <rank>" when RequiredRank > 0
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

MASTER_PATH = "/Game/Systems/Building/Placeables/BP_Master_Placeables"
MASTER_DISK = os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_Master_Placeables.uasset")
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
LOCK_C = f"{LOCAL}/BPC_GA_Lock.BPC_GA_Lock_C"
PLAYER_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
LOCK_ICON = "/Game/UI/Textures/GUIs/MainRadialMenu/MainRadialMenuIconLocked.MainRadialMenuIconLocked"
RANKS = [("Recruit", "Everyone in the clan"), ("Member", "Members and above"), ("Officer", "Officers and the guild master"), ("Guild Master", "Guild master only")]

sec(f"mode = {MODE}")
if MODE not in ("dry", "real"): print("unknown GA_MODE"); sys.exit(2)
wait_registry()
master = unreal.load_asset(MASTER_PATH); check(master is not None, "loaded Master override")
lock_cls = unreal.load_class(None, LOCK_C); player_cls = unreal.load_class(None, PLAYER_C)
check(lock_cls is not None and player_cls is not None, "loaded BPC_GA_Lock_C / BPC_GA_Player_C")
st0 = os.stat(MASTER_DISK)
ed = GE.get_graph_editor_by_name(master, "EventGraph"); check(ed is not None, "EventGraph editor")

def bpl_call(g, fn): return call(g, f"{BPL_C}:{fn}", fn)
def get_var(g, name, cls_path=""):
    n = g.add_get_member_variable_node(name, cls_path) if cls_path else g.add_get_member_variable_node(name)
    check(n is not None, f"Get {name}"); return n
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    outs = [p for p in lib.list_output_pins(n)]
    return outs[0] if outs else None
def rank_text_node(g, rank_pin):
    """Text: RankToText(rank)"""
    rt = bpl_call(g, "RankToText"); connect(rank_pin, lib.find_input_pin(rt, "Rank"), "rank -> RankToText")
    return lib.find_output_pin(rt, "Result")
def str_text(g, prefix_lit, text_pin):
    """Text: prefix + ToString(text_pin)"""
    t2s = call(g, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "TextToString")
    connect(text_pin, lib.find_input_pin(t2s, "InText"), "text -> ToString")
    cc = call(g, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat"); setval(cc, "A", prefix_lit)
    connect(lib.find_output_pin(t2s, "ReturnValue"), lib.find_input_pin(cc, "B"), "string -> Concat.B")
    s2t = call(g, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "StringToText")
    connect(lib.find_output_pin(cc, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "Concat -> ToText")
    return lib.find_output_pin(s2t, "ReturnValue")

# ============================================================================ 1. SCS component
sec("1. SCS component GuildAccessLock (BPC_GA_Lock)")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
check(sds is not None, "SubobjectDataSubsystem")
SDL = unreal.SubobjectDataBlueprintFunctionLibrary
lock_template = None
handles = list(sds.k2_gather_subobject_data_for_blueprint(master))
root = None
for h in handles:
    d = sds.k2_find_subobject_data_from_handle(h)
    obj = SDL.get_object(d)
    if SDL.is_root_actor(d) if hasattr(SDL, "is_root_actor") else False: root = h
    if root is None and obj is not None and isinstance(obj, unreal.Actor): root = h
    if obj is not None and obj.get_class().get_path_name() == LOCK_C:
        lock_template = obj; print("   existing SCS lock component:", obj.get_name())
if lock_template is None:
    check(root is not None, f"found root actor handle among {len(handles)} subobjects")
    params = unreal.AddNewSubobjectParams(parent_handle=root, new_class=lock_cls, blueprint_context=master)
    res = sds.add_new_subobject(params)
    new_handle, why = (res[0], res[1]) if isinstance(res, (tuple, list)) else (res, None)
    d = sds.k2_find_subobject_data_from_handle(new_handle) if new_handle else None
    lock_template = SDL.get_object(d) if d else None
    check(lock_template is not None, f"added SCS component ({why})")
    if lock_template is not None:
        try: print("   rename ->", sds.rename_subobject(new_handle, unreal.Text("GuildAccessLock")))
        except Exception as e: print("   rename raised", type(e).__name__, str(e)[:80])
check(lib.compile_blueprint(master), "compile Master after SCS change")
lock_var = None
for v in lib.list_member_variable_names(master):
    if lock_template is not None and str(v) == lock_template.get_name().replace("_GEN_VARIABLE", ""): lock_var = str(v)
print("   component variable name:", lock_var, "| template:", lock_template.get_name() if lock_template else None)

# ============================================================================ 2. server handler
sec("2. server handler: OnComponentActivated(GuildAccessLock)")
existing = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_ComponentBoundEvent" and "OnComponentActivated" in title(n)]
if existing:
    print("   bound event exists; leaving handler as is")
elif lock_template is not None:
    bev = ed.add_component_bound_event_node(lock_template, "OnComponentActivated")
    check(bev is not None, f"component bound event -> {title(bev) if bev else None} {pins(bev) if bev else ''}")
    ha = call(ed, "/Script/Engine.Actor:HasAuthority", "HasAuthority")
    br_auth = ed.add_branch_node()
    connect(then_out(bev), exec_in(br_auth), "event -> Branch(authority)")
    connect(lib.find_output_pin(ha, "ReturnValue"), lib.find_condition_pin(br_auth), "HasAuthority -> Condition")
    lockget = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(BPC_GA_Lock) on self"); setval(lockget, "ComponentClass", LOCK_C)
    lock_pin = lib.find_output_pin(lockget, "ReturnValue")
    inst = get_var(ed, "PendingInstigator", LOCK_C); connect(lock_pin, lib.find_self_pin(inst) or lib.find_input_pin(inst, "self"), "lock -> Get PendingInstigator.self")
    newr = get_var(ed, "PendingRank", LOCK_C); connect(lock_pin, lib.find_self_pin(newr) or lib.find_input_pin(newr, "self"), "lock -> Get PendingRank.self")
    inst_pin, newr_pin = out(inst, "PendingInstigator"), out(newr, "PendingRank")
    gp = call(ed, "/Script/Engine.Controller:K2_GetPawn", "GetPawn"); connect(inst_pin, lib.find_self_pin(gp) or lib.find_input_pin(gp, "self"), "instigator -> GetPawn.self")
    pawn = lib.find_output_pin(gp, "ReturnValue")
    gpr = bpl_call(ed, "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank")
    connect(then_out(br_auth), exec_in(gpr), "Branch.then -> GetPawnRank")
    castpc = create_by_search(ed, [inst_pin], ("Cast", "ConanPlayerController"), "Cast To ConanPlayerController", exact="Utilities|Casting|CastToConanPlayerController")
    connect(inst_pin, lib.find_input_pin(castpc, "Object"), "instigator -> Cast.Object")
    connect(then_out(gpr), exec_in(castpc), "GetPawnRank -> Cast")
    pc_pin = as_pin(castpc)
    isown = call(ed, "/Script/ConanSandbox.BuildableBase:IsOwner", "IsOwner"); connect(pawn, lib.find_input_pin(isown, "Pawn"), "pawn -> IsOwner.Pawn"); setval(isown, "bSendGuiNotification", "false")
    req = get_var(ed, "RequiredRank")
    can = bpl_call(ed, "RankCanSetRequired"); connect(lib.find_output_pin(gpr, "Rank"), lib.find_input_pin(can, "Rank"), "rank -> CanSet.Rank"); connect(out(req), lib.find_input_pin(can, "CurrentRequired"), "RequiredRank -> CanSet.Current")
    andn = call(ed, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND"); connect(lib.find_output_pin(isown, "ReturnValue"), lib.find_input_pin(andn, "A"), "IsOwner -> AND.A"); connect(lib.find_output_pin(can, "Result"), lib.find_input_pin(andn, "B"), "CanSet -> AND.B")
    br_perm = ed.add_branch_node(); connect(then_out(castpc), exec_in(br_perm), "Cast.then -> Branch(permission)"); connect(lib.find_output_pin(andn, "ReturnValue"), lib.find_condition_pin(br_perm), "AND -> Condition")
    le = call(ed, "/Script/Engine.KismetMathLibrary:LessEqual_ByteByte", "NewRank <= 3"); connect(newr_pin, lib.find_input_pin(le, "A"), "NewRank -> <=.A"); setval(le, "B", "3")
    br_valid = ed.add_branch_node(); connect(then_out(br_perm), exec_in(br_valid), "permission.then -> Branch(valid)"); connect(lib.find_output_pin(le, "ReturnValue"), lib.find_condition_pin(br_valid), "<=3 -> Condition")
    setr = ed.add_set_member_variable_node("RequiredRank"); check(setr is not None, "Set RequiredRank")
    connect(newr_pin, lib.find_input_pin(setr, "RequiredRank"), "NewRank -> Set RequiredRank"); connect(then_out(br_valid), exec_in(setr), "valid.then -> Set RequiredRank")
    pers = get_var(ed, "ConanBuildingPersistence")
    print("   dirty-related actions on the persistence pin:", available(ed, [out(pers)], "dirty")[:10])
    sd = create_by_search(ed, [out(pers)], ("SetDirty",), "SetDirty")
    if sd is not None:
        print("   SetDirty pins:", pins(sd))
        sp = lib.find_self_pin(sd) or lib.find_input_pin(sd, "self")
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(pers), sp, "persistence -> SetDirty.self")
        for pn in ("bDirty", "Dirty", "dirty"):
            if lib.find_input_pin(sd, pn) is not None: setval(sd, pn, "true"); break
        connect(then_out(setr), exec_in(sd), "Set -> SetDirty")
    notify_ok = call(ed, "/Script/ConanSandbox.ConanPlayerController:ClientHUDShowNotification", "notify ok")
    connect(pc_pin, lib.find_self_pin(notify_ok) or lib.find_input_pin(notify_ok, "self"), "PC -> notify.self")
    connect(str_text(ed, "Access rank set to ", rank_text_node(ed, newr_pin)), lib.find_input_pin(notify_ok, "text"), "text -> notify ok")
    connect(then_out(sd) if sd is not None else then_out(setr), exec_in(notify_ok), "-> notify ok")
    notify_no = call(ed, "/Script/ConanSandbox.ConanPlayerController:ClientHUDShowNotification", "notify denied")
    connect(pc_pin, lib.find_self_pin(notify_no) or lib.find_input_pin(notify_no, "self"), "PC -> notify denied.self")
    deny_txt = call(ed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "denied text"); setval(deny_txt, "InString", "You cannot change this access rank")
    connect(lib.find_output_pin(deny_txt, "ReturnValue"), lib.find_input_pin(notify_no, "text"), "denied text -> notify"); setval(notify_no, "positive", "false")
    connect(lib.find_else_pin(br_perm), exec_in(notify_no), "permission.else -> notify denied")

# ============================================================================ 3. radial menu
sec("3. radial menu: Set Access Rank + 4 rank sub-items")
if any("SetAccessRank" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "") for n in nodes_titled(ed, "AddItem") if lib.find_input_pin(n, "label")):
    print("   menu item exists; leaving menu as is")
else:
    ev_menu = nodes_titled(ed, "Event InteractableMenu"); check(len(ev_menu) == 1, "Event InteractableMenu found"); ev_menu = ev_menu[0]
    radial = lib.find_output_pin(ev_menu, "RadialMenu")
    seq = None
    for n in ed.list_all_nodes():
        if n.get_class().get_name() == "K2Node_ExecutionSequence":
            for p in lib.list_output_pins(n):
                if any("HandleLockableContainers" in title(PL.get_owning_node(c)) for c in PL.list_connected_pins(p)): seq = n
    check(seq is not None, "owner-menu Sequence found (feeds HandleLockableContainers)")
    before_pins = [str(PL.get_pin_name(p)) for p in lib.list_output_pins(seq)]
    check(ed.add_node_pin(seq), "Sequence: add pin")
    newpin = [p for p in lib.list_output_pins(seq) if str(PL.get_pin_name(p)) not in before_pins]
    check(len(newpin) == 1, f"new sequence pin {[str(PL.get_pin_name(p)) for p in newpin]}"); newpin = newpin[0]
    gopp = call(ed, "/Script/UMG.UserWidget:GetOwningPlayerPawn", "GetOwningPlayerPawn"); connect(radial, lib.find_self_pin(gopp) or lib.find_input_pin(gopp, "self"), "RadialMenu -> GetOwningPlayerPawn.self")
    gpr2 = bpl_call(ed, "GetPawnRank"); connect(lib.find_output_pin(gopp, "ReturnValue"), lib.find_input_pin(gpr2, "Pawn"), "pawn -> GetPawnRank (menu)")
    connect(newpin, exec_in(gpr2), "Sequence.new -> GetPawnRank")
    req2 = get_var(ed, "RequiredRank")
    can2 = bpl_call(ed, "RankCanSetRequired"); connect(lib.find_output_pin(gpr2, "Rank"), lib.find_input_pin(can2, "Rank"), "rank -> CanSet"); connect(out(req2), lib.find_input_pin(can2, "CurrentRequired"), "RequiredRank -> CanSet")
    br_menu = ed.add_branch_node(); connect(then_out(gpr2), exec_in(br_menu), "GetPawnRank -> Branch(menu)"); connect(lib.find_output_pin(can2, "Result"), lib.find_condition_pin(br_menu), "CanSet -> Condition")
    add = call(ed, "/Script/ConanSandbox.RadialMenu:AddItem", "AddItem (Set Access Rank)")
    connect(radial, lib.find_self_pin(add) or lib.find_input_pin(add, "self"), "RadialMenu -> AddItem.self")
    setval(add, "label", text_lit("SetAccessRank", "Set Access Rank")); setval(add, "icon", LOCK_ICON)
    connect(str_text(ed, "Current: ", rank_text_node(ed, out(req2))), lib.find_input_pin(add, "subtitle"), "subtitle -> AddItem")
    connect(then_out(br_menu), exec_in(add), "Branch.then -> AddItem")
    entry = lib.find_output_pin(add, "ReturnValue"); tail = then_out(add)
    selfnode = create_by_search(ed, [], ("Getareferencetoself",), "Self", exact="Variables|Getareferencetoself")
    self_pin = out(selfnode) if selfnode else None
    for i, (name, desc) in enumerate(RANKS):
        sub = call(ed, "/Script/ConanSandbox.RadialMenuEntry:AddSubItem", f"AddSubItem {name}")
        connect(entry, lib.find_self_pin(sub) or lib.find_input_pin(sub, "self"), f"entry -> AddSubItem[{i}].self")
        setval(sub, "label", text_lit(f"Rank{i}Label", name)); setval(sub, "subtitle", text_lit(f"Rank{i}Desc", desc)); setval(sub, "icon", LOCK_ICON)
        connect(tail, exec_in(sub), f"-> AddSubItem[{i}]")
        subrv = lib.find_output_pin(sub, "ReturnValue")
        lib.compile_blueprint(master)   # so the next Assign picks a unique event name
        before = snapshot(ed)
        asg = create_by_search(ed, [subrv], ("Assign", "SignalClicked"), f"Assign SignalClicked [{i}]", exact="Menu|Event|AssignSignalClicked")
        new = new_nodes(ed, before)
        cev = [n for n in new if n.get_class().get_name() == "K2Node_CustomEvent"]
        check(len(cev) == 1, f"click event created for rank {i} ({[title(n) for n in new]})")
        sp = lib.find_self_pin(asg) or lib.find_input_pin(asg, "self")
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(subrv, sp, f"sub-item -> Assign[{i}].self")
        connect(then_out(sub), exec_in(asg), f"AddSubItem[{i}].then -> Assign")
        tail = then_out(asg)
        if cev:
            h = cev[0]
            pc0 = call(ed, "/Script/Engine.GameplayStatics:GetPlayerController", "GetPlayerController(0)")
            gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(BPC_GA_Player)")
            connect(lib.find_output_pin(pc0, "ReturnValue"), lib.find_input_pin(gcb, "self"), "PC -> GetComponentByClass.self"); setval(gcb, "ComponentClass", PLAYER_C)
            rpc = call(ed, f"{PLAYER_C}:ServerSetRequiredRank_0", "ServerSetRequiredRank")
            connect(lib.find_output_pin(gcb, "ReturnValue"), lib.find_self_pin(rpc) or lib.find_input_pin(rpc, "self"), "component -> RPC.self")
            connect(self_pin, lib.find_input_pin(rpc, "Target"), "self -> RPC.Target"); setval(rpc, "NewRank", str(i))
            connect(then_out(h), exec_in(rpc), f"click[{i}] -> RPC")

# ============================================================================ 4. hover text
sec("4. hover text: InteractableGetSimpleDisplayText")
hed = GE.get_graph_editor_by_name(master, "InteractableGetSimpleDisplayText"); check(hed is not None, "hover graph editor")
if any(n.get_class().get_name() == "K2Node_IfThenElse" for n in hed.list_all_nodes()):
    print("   hover graph already modified; leaving as is")
else:
    entry_pin = hed.find_graph_entry_pin()
    ret0 = [n for n in hed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"]; check(len(ret0) == 1, "existing Return Node"); ret0 = ret0[0]
    PL.break_pin_links(entry_pin)
    req3 = get_var(hed, "RequiredRank")
    gt = call(hed, "/Script/Engine.KismetMathLibrary:Greater_ByteByte", "RequiredRank > 0"); connect(out(req3), lib.find_input_pin(gt, "A"), "RequiredRank -> >.A"); setval(gt, "B", "0")
    br = hed.add_branch_node(); connect(entry_pin, exec_in(br), "entry -> Branch"); connect(lib.find_output_pin(gt, "ReturnValue"), lib.find_condition_pin(br), "> -> Condition")
    connect(lib.find_else_pin(br), exec_in(ret0), "Branch.else -> original Return")
    ret1 = hed.add_return_node(); check(ret1 is not None, "second Return Node"); connect(then_out(br), exec_in(ret1), "Branch.then -> Return(text)")
    gbn = call(hed, "/Script/ConanSandbox.BuildableBase:GetBuildableName", "GetBuildableName"); setval(gbn, "ignoreCustomName", "false")
    n2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "name ToString"); connect(lib.find_output_pin(gbn, "ReturnValue"), lib.find_input_pin(n2s, "InText"), "name -> ToString")
    r2s = call(hed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "rank ToString"); connect(rank_text_node(hed, out(req3)), lib.find_input_pin(r2s, "InText"), "RankToText -> ToString")
    c1 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat 1"); setval(c1, "A", " - Requires "); connect(lib.find_output_pin(r2s, "ReturnValue"), lib.find_input_pin(c1, "B"), "rank -> Concat1.B")
    c2 = call(hed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat 2"); connect(lib.find_output_pin(n2s, "ReturnValue"), lib.find_input_pin(c2, "A"), "name -> Concat2.A"); connect(lib.find_output_pin(c1, "ReturnValue"), lib.find_input_pin(c2, "B"), "Concat1 -> Concat2.B")
    s2t = call(hed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "ToText"); connect(lib.find_output_pin(c2, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "Concat2 -> ToText")
    rvpin = lib.find_input_pin(ret1, "ReturnValue")
    connect(lib.find_output_pin(s2t, "ReturnValue"), rvpin, "text -> Return.ReturnValue")
dump(hed, "InteractableGetSimpleDisplayText")

# ============================================================================ compile + dump + save
sec("compile")
compile_ok(master, [(ed, "EventGraph"), (hed, "InteractableGetSimpleDisplayText")], "BP_Master_Placeables")
sec("dump: GuildAccess nodes in EventGraph")
keys = ("GuildAccessLock", "OnComponentActivated", "PendingRank", "PendingInstigator", "RankCanSetRequired", "RankToText", "AddSubItem", "SignalClicked", "ServerSetRequiredRank", "Set RequiredRank", "SetDirty", "ClientHUDShowNotification", "GetPlayerController", "Self")
for n in ed.list_all_nodes():
    t = title(n)
    if any(k in t for k in keys) or (t == "AddItem" and "SetAccessRank" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "")):
        print(f"   NODE [{n.get_class().get_name()}] {t!r}")
        for p in lib.list_all_pins(n):
            d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
            conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
            v = PL.get_pin_value(p)
            if v or conns: print(f"      {d} {str(PL.get_pin_name(p)):24} val={v[:60]!r:62} -> {conns}")
if MODE == "real" and not failures:
    sec("save Master override")
    save(master, MASTER_DISK, "BP_Master_Placeables override")
elif MODE == "real": print("\n   NOT SAVING: failures above")
result()
