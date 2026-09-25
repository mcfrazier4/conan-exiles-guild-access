"""v2 stage 4b - opening the panel. Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=player|container|door|builddoor. Idempotent.

player     : after ClientClanTable stores the cache -> CreateWidget(W_GA_ClanRanks) -> AddToViewport -> Game+UI input, cursor on
container / door / builddoor : a 'Clan Ranks' entry on the radial menu for every clan member
             -> local PlayerController.BPC_GA_Player.Server_ServerRequestClanTable
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "player").lower()
PL_PATH = f"{LOCAL}/BPC_GA_Player"; PL_C = f"{PL_PATH}.BPC_GA_Player_C"; W_C = f"{LOCAL}/W_GA_ClanRanks.W_GA_ClanRanks_C"
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"
CLASSES = {"container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
           "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset"),
           "builddoor": ("/Game/Systems/Building/BP_BuildDoor", r"Systems\Building\BP_BuildDoor.uasset")}
GM_BADGE = "/Game/UI/Textures/GUIs/Guild/T_Rank_GuildMaster.T_Rank_GuildMaster"
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")

if TARGET == "player":
    pl = unreal.load_asset(PL_PATH); ed = GE.get_graph_editor_by_name(pl, "EventGraph")
    if nodes_titled(ed, "Create Widget") or any("CreateWidget" in n.get_class().get_name() for n in ed.list_all_nodes()): print("   exists")
    else:
        setr = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_VariableSet" and title(n) == "Set TableReady"]
        check(len(setr) == 1, "Set TableReady node"); setr = setr[0]
        own = call(ed, "/Script/Engine.ActorComponent:GetOwner", "GetOwner")
        cast = create_by_search(ed, [out(own, "ReturnValue")], ("Cast", "PlayerController"), "Cast To PlayerController", exact="Utilities|Casting|CastToPlayerController")
        connect(out(own, "ReturnValue"), pin_exact_in(cast, "Object"), "owner -> cast"); connect(then_out(setr), exec_in(cast), "TableReady -> cast")
        cw = create_by_search(ed, [], ("CreateWidget",), "Create Widget", exact="UserInterface|CreateWidget"); print("   CreateWidget pins:", pins(cw))
        check(PL.set_pin_value(pin_exact_in(cw, "Class"), W_C), "widget class")
        connect(as_pin(cast), pin_exact_in(cw, "OwningPlayer"), "PC -> OwningPlayer"); connect(then_out(cast), exec_in(cw), "cast -> CreateWidget")
        atv = call(ed, "/Script/UMG.UserWidget:AddToViewport", "AddToViewport"); connect(out(cw, "ReturnValue"), selfpin(atv), "widget -> AddToViewport"); setval(atv, "ZOrder", "100"); connect(then_out(cw), exec_in(atv), "-> AddToViewport")
        im = call(ed, "/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameAndUIEx", "SetInputModeGameAndUI"); connect(as_pin(cast), pin_exact_in(im, "PlayerController"), "PC"); connect(out(cw, "ReturnValue"), pin_exact_in(im, "InWidgetToFocus"), "widget"); connect(then_out(atv), exec_in(im), "-> input mode")
        smc = ed.add_set_member_variable_node("bShowMouseCursor", "/Script/Engine.PlayerController"); connect(as_pin(cast), selfpin(smc), "PC"); PL.set_pin_value(pin_exact_in(smc, "bShowMouseCursor"), "true"); connect(then_out(im), exec_in(smc), "-> cursor on")
    compile_ok(pl, [(ed, "EventGraph")], "BPC_GA_Player")
    if MODE == "real" and not failures: save(pl, os.path.join(DISK_LOCAL, "BPC_GA_Player.uasset"), "BPC_GA_Player")
else:
    PATH, REL = CLASSES[TARGET]; bp = unreal.load_asset(PATH); ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    if any("ClanRanks" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "") for n in nodes_titled(ed, "AddItem") if lib.find_input_pin(n, "label")): print("   exists")
    else:
        add = [n for n in nodes_titled(ed, "AddItem") if "SetAccessRank" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "")]
        check(len(add) == 1, "Set Access Rank AddItem"); add = add[0]
        br = [PL.get_owning_node(c) for c in PL.list_connected_pins(exec_in(add))]; check(len(br) == 1 and br[0].get_class().get_name() == "K2Node_IfThenElse", "its Branch"); br = br[0]
        feeder = list(PL.list_connected_pins(exec_in(br))); check(len(feeder) == 1, "Branch fed by one exec"); feeder = feeder[0]
        gpr = PL.get_owning_node(feeder); check(title(gpr) == "GetPawnRank", f"fed by GetPawnRank ({title(gpr)})")
        radial = list(PL.list_connected_pins(selfpin(add)))[0]
        seq = create_by_search(ed, [], ("FlowControl", "Sequence"), "Sequence", exact="Utilities|FlowControl|Sequence")
        PL.break_pin_links(feeder); connect(feeder, exec_in(seq), "GetPawnRank -> Sequence"); connect(pin_exact_out(seq, "then_0"), exec_in(br), "then_0 -> rank Branch")
        igm = call(ed, f"{BPL_C}:IsGuildMemberRank", "IsGuildMemberRank"); connect(out(gpr, "Rank"), pin_exact_in(igm, "Rank"), "rank -> member"); connect(pin_exact_out(seq, "then_1"), exec_in(igm), "then_1 -> member")
        br2 = ed.add_branch_node(); connect(then_out(igm), exec_in(br2), "member -> Branch"); connect(out(igm, "Result"), lib.find_condition_pin(br2), "member?")
        a2 = call(ed, "/Script/ConanSandbox.RadialMenu:AddItem", "AddItem(Clan Ranks)"); connect(radial, selfpin(a2), "RadialMenu -> AddItem")
        setval(a2, "label", text_lit("ClanRanks", "Clan Ranks")); setval(a2, "subtitle", text_lit("ClanRanksSub", "Rank names and permissions")); setval(a2, "icon", GM_BADGE)
        connect(then_out(br2), exec_in(a2), "-> AddItem")
        lib.compile_blueprint(bp)
        before = snapshot(ed)
        asg = create_by_search(ed, [out(a2, "ReturnValue")], ("Assign", "SignalClicked"), "Assign SignalClicked", exact="Menu|Event|AssignSignalClicked")
        h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, "click handler"); h = h[0]
        sp = selfpin(asg)
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(a2, "ReturnValue"), sp, "entry -> Assign.self")
        connect(then_out(a2), exec_in(asg), "AddItem -> Assign")
        pc0 = call(ed, "/Script/Engine.GameplayStatics:GetPlayerController", "GetPlayerController(0)")
        gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(out(pc0, "ReturnValue"), pin_exact_in(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
        rpc = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "ServerRequestClanTable"); connect(out(gcb, "ReturnValue"), selfpin(rpc), "component -> rpc"); connect(then_out(h), exec_in(rpc), "click -> rpc")
    compile_ok(bp, [(ed, "EventGraph")], TARGET)
    if MODE == "real" and not failures: save(bp, os.path.join(DISK_CONTENT, REL), TARGET)
if MODE == "real" and failures: print("   NOT SAVING: failures above")
result()
