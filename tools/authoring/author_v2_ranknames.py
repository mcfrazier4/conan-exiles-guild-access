"""v2 - per-clan rank names everywhere the mod prints a rank. Run WITH -ModDevKit. GA_MODE=dry|real.
GA_TARGET=bpl | container | door | builddoor. Idempotent.

bpl   : RankToText(Rank) now prefers the local player's clan cache (BPC_GA_Player.CachedNames when TableReady) and falls
        back to the built-in names. Used by the radial labels and hover text (client side).
        New RankNameServer(Controller, Rank) -> Text: the controller's pawn's guild -> BP_GA_ModController.GetRankName.
        Used by the server-built denial messages.
leaf  : every EventGraph RankToText whose text ends in ClientHUDShowNotification is replaced by RankNameServer fed by the
        controller that receives the notification (the Cast To ConanPlayerController's input).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "bpl").lower()
BPL_PATH = f"{LOCAL}/BPL_GuildAccess"; BPL_C = f"{BPL_PATH}.BPL_GuildAccess_C"; PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"; MOD_C = f"{LOCAL}/BP_GA_ModController.BP_GA_ModController_C"
CLASSES = {"container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
           "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset"),
           "builddoor": ("/Game/Systems/Building/BP_BuildDoor", r"Systems\Building\BP_BuildDoor.uasset")}
M = "/Script/Engine.KismetMathLibrary:"; T = "/Script/Engine.KismetTextLibrary:"
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def first_param(n): return next((p for p in lib.list_input_pins(n) if str(PL.get_pin_name(p)) not in ("self", "execute")), None)
def array_get(ed, arr_pin, idx_pin):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), "array -> Get"); connect(idx_pin, pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index"), "index -> Get"); return out(g)
if TARGET == "bpl":
    bpl = unreal.load_asset(BPL_PATH); check(bpl is not None, "loaded BPL")
    byte_t, text_t = lib.get_basic_type_by_name("byte"), lib.get_basic_type_by_name("text")
    # --- RankToText: cache first
    ed = GE.get_graph_editor_by_name(bpl, "RankToText")
    if nodes_titled(ed, "GetComponentByClass"): print("   RankToText already cache-aware")
    else:
        ret = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"][0]; entry = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionEntry"][0]
        rp = pin_exact_in(ret, "Result"); default_src = list(PL.list_connected_pins(rp)); check(len(default_src) == 1, "Result fed by one node"); default_src = default_src[0]
        PL.break_pin_links(rp)
        pc0 = call(ed, "/Script/Engine.GameplayStatics:GetPlayerController", "GetPlayerController(0)"); setval(pc0, "PlayerIndex", "0")
        gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(out(pc0, "ReturnValue"), selfpin(gcb), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
        comp = out(gcb, "ReturnValue")   # GetComponentByClass types its output by the class literal
        iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", "IsValid(comp)"); connect(comp, pin_exact_in(iv, "Object"), "comp")
        ready = ed.add_get_member_variable_node("TableReady", PL_C); connect(comp, selfpin(ready), "comp")
        names = ed.add_get_member_variable_node("CachedNames", PL_C); connect(comp, selfpin(names), "comp")
        ln = create_by_search(ed, [out(names)], ("Array", "Length"), "Length", exact="Utilities|Array|Length"); connect(out(names), pin_exact_in(ln, "TargetArray"), "names -> Length")
        eq4 = call(ed, M + "EqualEqual_IntInt", "len==4"); connect(out(ln), pin_exact_in(eq4, "A"), "len"); setval(eq4, "B", "4")
        and1 = call(ed, M + "BooleanAND", "valid AND ready"); connect(out(iv, "ReturnValue"), pin_exact_in(and1, "A"), "valid"); connect(out(ready), pin_exact_in(and1, "B"), "ready")
        and2 = call(ed, M + "BooleanAND", "AND len==4"); connect(out(and1, "ReturnValue"), pin_exact_in(and2, "A"), "a"); connect(out(eq4, "ReturnValue"), pin_exact_in(and2, "B"), "len ok")
        b2i = call(ed, M + "Conv_ByteToInt", "Rank -> int"); connect(out(entry, "Rank"), pin_exact_in(b2i, "InByte"), "Rank")
        s2t = call(ed, T + "Conv_StringToText", "cached -> text"); connect(array_get(ed, out(names), out(b2i, "ReturnValue")), pin_exact_in(s2t, "InString"), "CachedNames[Rank]")
        sel = call(ed, M + "SelectText", "cache or default"); connect(out(s2t, "ReturnValue"), pin_exact_in(sel, "A"), "cache"); connect(default_src, pin_exact_in(sel, "B"), "default"); connect(out(and2, "ReturnValue"), pin_exact_in(sel, "bPickA"), "use cache?")
        connect(out(sel, "ReturnValue"), rp, "-> Result")
    compile_ok(bpl, [(ed, "RankToText")], "RankToText")
    # --- RankNameServer(Controller, Rank) -> Text
    if "RankNameServer" in [str(g) for g in lib.list_graph_names(bpl)]: print("   RankNameServer exists"); ed2 = GE.get_graph_editor_by_name(bpl, "RankNameServer")
    else:
        g = lib.add_function_graph(bpl, "RankNameServer"); ed2 = GE.get_graph_editor(g)
        ctrl = ed2.add_graph_input_parameter("Controller", lib.get_object_reference_type(unreal.PlayerController), ""); rank = ed2.add_graph_input_parameter("Rank", byte_t, ""); ret = ed2.add_graph_output_parameter("Result", text_t)
        check(ctrl is not None and rank is not None and ret is not None, "RankNameServer params")
        entry = [n for n in ed2.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionEntry"][0]; t = then_out(entry)
        pawn = call(ed2, "/Script/Engine.Controller:K2_GetPawn", "GetControlledPawn"); connect(ctrl, selfpin(pawn), "controller")
        cc = create_by_search(ed2, [out(pawn, "ReturnValue")], ("Casting", "CastToConanCharacter"), "Cast To ConanCharacter", exact="Utilities|Casting|CastToConanCharacter"); connect(out(pawn, "ReturnValue"), pin_exact_in(cc, "Object"), "pawn -> cast")
        if pin_exact_in(cc, "execute") is not None: connect(t, pin_exact_in(cc, "execute"), "-> cast"); t = pin_exact_out(cc, "then")
        gid = call(ed2, "/Script/ConanSandbox.ConanCharacter:GetGuildStableId", "GetGuildStableId"); connect(as_pin(cc), selfpin(gid), "char")
        if pin_exact_in(gid, "execute") is not None: connect(t, pin_exact_in(gid, "execute"), "-> guild id"); t = pin_exact_out(gid, "then")
        conv = call(ed2, unreal.StableIdFunctionLibrary.static_class().get_path_name() + ":Conv_StableIdToString", "StableId -> String"); connect(out(gid, "ReturnValue"), lib.list_input_pins(conv)[0], "id")
        gc = call(ed2, f"{BPL_C}:GetGAController", "GetGAController"); connect(t, exec_in(gc), "-> GetGAController"); t = then_out(gc)
        grn = call(ed2, f"{MOD_C}:GetRankName", "GetRankName"); connect(out(gc, "Controller"), selfpin(grn), "ctrl"); connect(out(conv, "ReturnValue"), pin_exact_in(grn, "GuildId"), "guild"); connect(rank, pin_exact_in(grn, "Rank"), "rank")
        if pin_exact_in(grn, "execute") is not None: connect(t, pin_exact_in(grn, "execute"), "-> GetRankName"); t = pin_exact_out(grn, "then")
        s2t = call(ed2, T + "Conv_StringToText", "-> text"); connect(out(grn, "Name"), pin_exact_in(s2t, "InString"), "name"); connect(out(s2t, "ReturnValue"), pin_exact_in(ret, "Result"), "-> Result")
        connect(t, exec_in(ret), "-> return")
    compile_ok(bpl, [(ed2, "RankNameServer")], "RankNameServer")
    if MODE == "real" and not failures: save(bpl, os.path.join(DISK_LOCAL, "BPL_GuildAccess.uasset"), "BPL_GuildAccess")
    elif MODE == "real": print("   NOT SAVING: failures above")
else:
    PATH, REL = CLASSES[TARGET]; bp = unreal.load_asset(PATH); ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    done = 0
    for n in [n for n in ed.list_all_nodes() if title(n) == "RankToText"]:
        cons = [PL.get_owning_node(c) for q in lib.list_output_pins(n) for c in PL.list_connected_pins(q)]
        cur = cons[0] if cons else None; hops = 0; notif = None
        while cur is not None and hops < 6:
            if title(cur) == "ClientHUDShowNotification": notif = cur; break
            nxt = [PL.get_owning_node(c) for q in lib.list_output_pins(cur) for c in PL.list_connected_pins(q)]; cur = nxt[0] if nxt else None; hops += 1
        if notif is None: continue   # client-side radial / hover label: RankToText handles the cache
        cast_src = list(PL.list_connected_pins(selfpin(notif))); check(len(cast_src) == 1, "notification self source"); cast = PL.get_owning_node(cast_src[0])
        ctrl_src = as_pin(cast); check(ctrl_src is not None, "cast output (ConanPlayerController)")   # typed PlayerController; valid once the cast succeeded
        rank_src = list(PL.list_connected_pins(lib.find_input_pin(n, "Rank")))[0]
        ts = list(PL.list_connected_pins(lib.find_output_pin(n, "Result"))); check(len(ts) == 1, "RankToText consumer"); ts = ts[0]
        rns = call(ed, f"{BPL_C}:RankNameServer", "RankNameServer"); connect(ctrl_src, pin_exact_in(rns, "Controller"), "controller"); connect(rank_src, pin_exact_in(rns, "Rank"), "rank")
        PL.break_pin_links(lib.find_output_pin(n, "Result")); connect(out(rns, "Result"), ts, "RankNameServer -> text")
        # RankNameServer has exec pins (GetGAController is impure): splice it before the notification's exec predecessor
        pred = list(PL.list_connected_pins(exec_in(notif))); check(len(pred) == 1, "notification exec predecessor"); pred = pred[0]
        PL.break_pin_links(exec_in(notif)); connect(pred, exec_in(rns), "-> RankNameServer"); connect(then_out(rns), exec_in(notif), "-> notification")
        ed.remove_nodes([n]); done += 1
    print(f"   server sites rewired: {done}")
    compile_ok(bp, [(ed, "EventGraph")], TARGET)
    if MODE == "real" and not failures and done: save(bp, os.path.join(DISK_CONTENT, REL), TARGET)
    elif MODE == "real" and failures: print("   NOT SAVING: failures above")
result()
