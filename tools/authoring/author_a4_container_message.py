"""A4 - rank-aware container denial text. Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

BP_Master_Placeables :: ShouldDisableInteraction shows vanilla's 'Container is locked!'
when CanAccessContainer denies. On the exec path into that notification we now
compute the rank verdict (GetPawnRank -> IsGuildMemberRank / MeetsRankRequirement)
and pick the text with SelectText:
   rank-denied : 'Container is locked - requires <rank>'
   otherwise   : vanilla's literal, untouched
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

MASTER = "/Game/Systems/Building/Placeables/BP_Master_Placeables"
MASTER_DISK = os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_Master_Placeables.uasset")
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"

sec(f"mode = {MODE}")
wait_registry()
master = unreal.load_asset(MASTER); check(master is not None, "loaded Master override")
ed = GE.get_graph_editor_by_name(master, "ShouldDisableInteraction"); check(ed is not None, "ShouldDisableInteraction editor")

if any(title(n) == "SelectText" for n in ed.list_all_nodes()):
    print("   SelectText already present; leaving graph as is")
else:
    lit = None
    for n in ed.list_all_nodes():
        if title(n) == "MakeLiteralText":
            v = PL.get_pin_value(lib.find_input_pin(n, "Value")) or ""
            if "locked" in v.lower(): lit = n; print("   vanilla literal:", v[:120])
    check(lit is not None, "found the 'Container is locked' literal")
    lit_out = lib.find_output_pin(lit, "ReturnValue")
    note = [PL.get_owning_node(c) for c in PL.list_connected_pins(lit_out)]
    check(len(note) == 1 and title(note[0]) == "ClientHUDShowNotification", "literal feeds exactly one notification"); note = note[0]
    text_pin = lib.find_input_pin(note, "text")
    cast = [PL.get_owning_node(c) for c in PL.list_connected_pins(exec_in(note))]
    check(len(cast) == 1 and "Cast To ConanPlayerController" in title(cast[0]), "notification is preceded by the controller cast"); cast = cast[0]
    pred = list(PL.list_connected_pins(exec_in(cast)))
    check(len(pred) == 1, "cast has exactly one exec predecessor"); pred = pred[0]
    print("   exec predecessor:", title(PL.get_owning_node(pred)), PL.get_pin_name(pred))
    cac = nodes_titled(ed, "CanAccessContainer"); check(len(cac) == 1, "CanAccessContainer call in graph")
    pawn_src = list(PL.list_connected_pins(lib.find_input_pin(cac[0], "InteractingPawn")))
    check(len(pawn_src) == 1, "pawn source pin"); pawn = pawn_src[0]
    # rank verdict on the exec line before the cast
    gpr = call(ed, f"{BPL_C}:GetPawnRank", "GetPawnRank"); connect(pawn, lib.find_input_pin(gpr, "Pawn"), "pawn -> GetPawnRank")
    igm = call(ed, f"{BPL_C}:IsGuildMemberRank", "IsGuildMemberRank"); connect(lib.find_output_pin(gpr, "Rank"), lib.find_input_pin(igm, "Rank"), "rank -> IsGuildMemberRank")
    req = ed.add_get_member_variable_node("RequiredRank"); check(req is not None, "Get RequiredRank"); req_pin = lib.list_output_pins(req)[0]
    mrr = call(ed, f"{BPL_C}:MeetsRankRequirement", "MeetsRankRequirement")
    connect(lib.find_output_pin(gpr, "Rank"), lib.find_input_pin(mrr, "Rank"), "rank -> Meets.Rank"); connect(req_pin, lib.find_input_pin(mrr, "Required"), "RequiredRank -> Meets.Required")
    PL.break_pin_links(exec_in(cast))
    connect(pred, exec_in(gpr), "pred -> GetPawnRank"); connect(then_out(gpr), exec_in(igm), "GetPawnRank -> IsGuildMemberRank")
    connect(then_out(igm), exec_in(mrr), "IsGuildMemberRank -> Meets"); connect(then_out(mrr), exec_in(cast), "Meets -> Cast")
    notn = call(ed, "/Script/Engine.KismetMathLibrary:Not_PreBool", "NOT"); connect(lib.find_output_pin(mrr, "Result"), lib.find_input_pin(notn, "A"), "Meets -> NOT")
    andn = call(ed, "/Script/Engine.KismetMathLibrary:BooleanAND", "AND")
    connect(lib.find_output_pin(igm, "Result"), lib.find_input_pin(andn, "A"), "member -> AND.A"); connect(lib.find_output_pin(notn, "ReturnValue"), lib.find_input_pin(andn, "B"), "NOT -> AND.B")
    # our text
    rt = call(ed, f"{BPL_C}:RankToText", "RankToText"); connect(req_pin, lib.find_input_pin(rt, "Rank"), "RequiredRank -> RankToText")
    t2s = call(ed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "TextToString"); connect(lib.find_output_pin(rt, "Result"), lib.find_input_pin(t2s, "InText"), "RankToText -> ToString")
    cc = call(ed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat"); setval(cc, "A", "Container is locked - requires ")
    connect(lib.find_output_pin(t2s, "ReturnValue"), lib.find_input_pin(cc, "B"), "rank -> Concat.B")
    s2t = call(ed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "StringToText"); connect(lib.find_output_pin(cc, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "Concat -> ToText")
    sel = call(ed, "/Script/Engine.KismetMathLibrary:SelectText", "SelectText")
    connect(lib.find_output_pin(s2t, "ReturnValue"), lib.find_input_pin(sel, "A"), "our text -> Select.A")
    PL.break_pin_links(text_pin)
    connect(lit_out, lib.find_input_pin(sel, "B"), "vanilla literal -> Select.B")
    connect(lib.find_output_pin(andn, "ReturnValue"), lib.find_input_pin(sel, "bPickA"), "rank-denied -> Select.bPickA")
    connect(lib.find_output_pin(sel, "ReturnValue"), text_pin, "Select -> notification.text")
compile_ok(master, [(ed, "ShouldDisableInteraction")], "BP_Master_Placeables")
for n in ed.list_all_nodes():
    if title(n) in ("SelectText", "ClientHUDShowNotification", "GetPawnRank", "MeetsRankRequirement", "IsGuildMemberRank") or "Cast To ConanPlayerController" in title(n):
        print(f"   NODE {title(n)!r}:", [(str(PL.get_pin_name(p)), [f'{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}' for c in PL.list_connected_pins(p)]) for p in lib.list_all_pins(n) if list(PL.list_connected_pins(p))])
if MODE == "real" and not failures: save(master, MASTER_DISK, "BP_Master_Placeables")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
