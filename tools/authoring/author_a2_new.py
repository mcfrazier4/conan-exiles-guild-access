"""A2 part 1b - the three NEW Local Blueprints. Run WITH -ModDevKit.
GA_MODE=dry | real.  Idempotent; safe to run twice (second run fills anything missing).

  BPC_GA_Lock        ActorComponent. Payload for a rank-change request:
                     PendingRank: Byte, PendingInstigator: Controller.
                     The request SIGNAL is the native Activate(bReset=true) -> OnComponentActivated,
                     which the Master override binds to (Blueprint dispatchers cannot be wired headlessly).
  BPC_GA_Player      ActorComponent, Replicates. Event ServerSetRequiredRank(Target: Actor, NewRank: Byte)
                     (created from a same-named dispatcher signature; Run on Server + Reliable is a GUI tick):
                     Lock = Target.GetComponentByClass(BPC_GA_Lock); if valid:
                       Lock.PendingRank = NewRank; Lock.PendingInstigator = Owner as Controller; Lock.Activate(true)
  BP_GA_ModController  ModController; AdditionalClassComponents = [FunCombat_PlayerController_C <- BPC_GA_Player, SERVER]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

LOCK_PATH = f"{LOCAL}/BPC_GA_Lock"
PLAYER_PATH = f"{LOCAL}/BPC_GA_Player"
MODCTRL_PATH = f"{LOCAL}/BP_GA_ModController"
PC_CLASS = "/Game/Systems/FunCombat_PlayerController.FunCombat_PlayerController_C"
byte_t = lib.get_basic_type_by_name("byte")

sec(f"mode = {MODE}")
if MODE not in ("dry", "real"): print("unknown GA_MODE"); sys.exit(2)

# ----------------------------------------------------------------------------- Lock component
sec("BPC_GA_Lock :: PendingRank (Byte), PendingInstigator (Controller)")
lock, lock_new = load_or_create(LOCK_PATH, unreal.ActorComponent)
if lock is None: result()
have = [str(v) for v in lib.list_member_variable_names(lock)]
if "PendingRank" not in have: check(lib.add_member_variable(lock, "PendingRank", byte_t), "variable PendingRank: Byte")
else: print("   PendingRank exists")
if "PendingInstigator" not in have: check(lib.add_member_variable(lock, "PendingInstigator", lib.get_object_reference_type(unreal.Controller)), "variable PendingInstigator: Controller")
else: print("   PendingInstigator exists")
compile_ok(lock, [], "BPC_GA_Lock")
lock_cls = lib.generated_class(lock); LOCK_CLS_PATH = lock_cls.get_path_name(); print("   Lock class:", LOCK_CLS_PATH)

# ----------------------------------------------------------------------------- Player component
sec("BPC_GA_Player :: ServerSetRequiredRank(Target, NewRank)")
player, player_new = load_or_create(PLAYER_PATH, unreal.ActorComponent)
if player is None: result()
disp = [str(x) for x in lib.list_event_dispatchers(player)]
if "ServerSetRequiredRank" not in disp:
    check(lib.add_event_dispatcher(player, "ServerSetRequiredRank"), "signature dispatcher ServerSetRequiredRank")
    check(lib.add_event_dispatcher_parameter(player, "ServerSetRequiredRank", "Target", lib.get_object_reference_type(unreal.Actor)), "param Target: Actor")
    check(lib.add_event_dispatcher_parameter(player, "ServerSetRequiredRank", "NewRank", byte_t), "param NewRank: Byte")
else: print("   signature dispatcher exists")
check(lib.compile_blueprint(player), "compile player component (skeleton needed for the event node)")
ped = GE.get_graph_editor_by_name(player, "EventGraph"); check(ped is not None, "player EventGraph editor")
player_cls = lib.generated_class(player)
evs = [n for n in ped.list_all_nodes() if n.get_class().get_name() == "K2Node_CustomEvent" and title(n).startswith("ServerSetRequiredRank")]
if evs:
    ev = evs[0]; print(f"   event {title(ev)!r} exists; leaving graph as is")
else:
    ev = ped.add_dispatcher_event_node("ServerSetRequiredRank")
    check(ev is not None and ev.get_class().get_name() == "K2Node_CustomEvent", f"custom event from dispatcher signature -> {title(ev) if ev else None} {pins(ev) if ev else ''}")
    tgt, nr = lib.find_output_pin(ev, "Target"), lib.find_output_pin(ev, "NewRank")
    check(tgt is not None and nr is not None, "event has Target + NewRank pins")
    gcb = call(ped, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass")
    connect(tgt, lib.find_input_pin(gcb, "self"), "Target -> GetComponentByClass.self")
    setval(gcb, "ComponentClass", LOCK_CLS_PATH)
    rvp = lib.find_output_pin(gcb, "ReturnValue")
    isv = call(ped, "/Script/Engine.KismetSystemLibrary:IsValid", "IsValid")
    connect(rvp, lib.find_input_pin(isv, "Object"), "component -> IsValid")
    br = ped.add_branch_node(); check(br is not None, "Branch")
    connect(then_out(ev), exec_in(br), "event.then -> Branch")
    connect(lib.find_output_pin(isv, "ReturnValue"), lib.find_condition_pin(br), "IsValid -> Branch.Condition")
    own = call(ped, "/Script/Engine.ActorComponent:GetOwner", "GetOwner")
    castc = create_by_search(ped, [lib.find_output_pin(own, "ReturnValue")], ("Cast", "Controller"), "Cast To Controller", exact="Utilities|Casting|CastToController")
    connect(lib.find_output_pin(own, "ReturnValue"), lib.find_input_pin(castc, "Object"), "Owner -> CastToController.Object")
    connect(then_out(br), exec_in(castc), "Branch.then -> CastToController")
    set_rank = ped.add_set_member_variable_node("PendingRank", LOCK_CLS_PATH); check(set_rank is not None, "Set PendingRank (on Lock)")
    set_inst = ped.add_set_member_variable_node("PendingInstigator", LOCK_CLS_PATH); check(set_inst is not None, "Set PendingInstigator (on Lock)")
    print("   Set PendingRank pins:", pins(set_rank), "| Set PendingInstigator pins:", pins(set_inst))
    connect(rvp, lib.find_self_pin(set_rank) or lib.find_input_pin(set_rank, "self"), "component -> SetPendingRank.self (output typed as Lock?)")
    connect(rvp, lib.find_self_pin(set_inst) or lib.find_input_pin(set_inst, "self"), "component -> SetPendingInstigator.self")
    connect(nr, lib.find_input_pin(set_rank, "PendingRank"), "NewRank -> SetPendingRank.value")
    connect(as_pin(castc), lib.find_input_pin(set_inst, "PendingInstigator"), "AsController -> SetPendingInstigator.value")
    connect(then_out(castc), exec_in(set_rank), "CastToController.then -> SetPendingRank")
    connect(then_out(set_rank), exec_in(set_inst), "SetPendingRank.then -> SetPendingInstigator")
    act = call(ped, "/Script/Engine.ActorComponent:Activate", "Activate")
    print("   Activate pins:", pins(act))
    connect(rvp, lib.find_self_pin(act) or lib.find_input_pin(act, "self"), "component -> Activate.self")
    setval(act, "bReset", "true")
    connect(then_out(set_inst), exec_in(act), "SetPendingInstigator.then -> Activate")
dump(ped, "BPC_GA_Player::EventGraph")
compile_ok(player, [(ped, "EventGraph")], "BPC_GA_Player")
try:
    cdo = unreal.get_default_object(player_cls)
    cdo.set_editor_property("replicates", True)
    check(bool(cdo.get_editor_property("replicates")), "player component CDO: Replicates = true")
except Exception as e: check(False, f"set Replicates on component CDO ({type(e).__name__}: {str(e)[:80]}) -> GUI step")
print("   functions on BPC_GA_Player:", [str(f.name) for f in lib.list_functions(player)])
print("   events on BPC_GA_Player:", [str(e.name) for e in lib.list_events(player) if e.is_implemented])

# ----------------------------------------------------------------------------- ModController
sec("BP_GA_ModController :: AdditionalClassComponents = [PlayerController <- BPC_GA_Player]")
mod, mod_new = load_or_create(MODCTRL_PATH, unreal.ModController)
if mod is None: result()
check(lib.compile_blueprint(mod), "compile ModController BP")
pc_cls = unreal.load_class(None, PC_CLASS); check(pc_cls is not None, f"loaded {PC_CLASS}")
try:
    cdo = unreal.get_default_object(lib.generated_class(mod))
    e1 = unreal.AdditionalClassComponent(target_actor_class=pc_cls, component_to_add=player_cls, addition_rule=unreal.AdditionalComponentRules.SERVER, component_tag="GuildAccess")
    cdo.set_editor_property("additional_class_components", [e1])
    back = list(cdo.get_editor_property("additional_class_components"))
    for x in back: print("   CDO entry:", x)
    check(len(back) == 1, "AdditionalClassComponents registered on the CDO")
except Exception as e:
    check(False, f"set additional_class_components ({type(e).__name__}: {str(e)[:120]}) -> GUI step")

if MODE == "real" and not failures:
    sec("save new Local packages")
    save(lock, os.path.join(DISK_LOCAL, "BPC_GA_Lock.uasset"), "BPC_GA_Lock")
    save(player, os.path.join(DISK_LOCAL, "BPC_GA_Player.uasset"), "BPC_GA_Player")
    save(mod, os.path.join(DISK_LOCAL, "BP_GA_ModController.uasset"), "BP_GA_ModController")
elif MODE == "real": print("\n   NOT SAVING: failures above")
result()
