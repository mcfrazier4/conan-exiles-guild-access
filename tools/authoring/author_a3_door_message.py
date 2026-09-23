"""A3 - denial message for placeable doors. Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

BP_PL_Door :: Event Custom Interaction: the A1 gate Branch's `else` (denied) now
casts the interacting controller to ConanPlayerController and shows
"Door is locked - requires <rank>" as a negative HUD notification.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

DOOR = "/Game/Systems/Building/Placeables/BP_PL_Door"
DOOR_DISK = os.path.join(DISK_CONTENT, r"Systems\Building\Placeables\BP_PL_Door.uasset")
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"

sec(f"mode = {MODE}")
wait_registry()
door = unreal.load_asset(DOOR); check(door is not None, "loaded door override")
ed = GE.get_graph_editor_by_name(door, "EventGraph"); check(ed is not None, "EventGraph editor")

# the gate: a Branch whose Condition comes from 'OR Boolean' and whose else pin is free
gate = None
for n in ed.list_all_nodes():
    if n.get_class().get_name() != "K2Node_IfThenElse": continue
    cond = lib.find_condition_pin(n)
    feeders = [title(PL.get_owning_node(c)) for c in PL.list_connected_pins(cond)]
    if feeders == ["OR Boolean"]: gate = n
check(gate is not None, "found the A1 gate Branch (Condition <- OR Boolean)")
else_pin = lib.find_else_pin(gate)
if list(PL.list_connected_pins(else_pin)):
    print("   gate.else already wired; leaving as is")
else:
    ev = nodes_titled(ed, "Event Custom Interaction"); check(len(ev) == 1, "Event Custom Interaction"); ev = ev[0]
    inst = lib.find_output_pin(ev, "Instigator")
    cast = create_by_search(ed, [inst], ("Cast", "ConanPlayerController"), "Cast To ConanPlayerController", exact="Utilities|Casting|CastToConanPlayerController")
    connect(inst, lib.find_input_pin(cast, "Object"), "Instigator -> Cast.Object")
    connect(else_pin, exec_in(cast), "gate.else -> Cast")
    req = ed.add_get_member_variable_node("RequiredRank"); check(req is not None, "Get RequiredRank")
    rt = call(ed, f"{BPL_C}:RankToText", "RankToText"); connect(lib.list_output_pins(req)[0], lib.find_input_pin(rt, "Rank"), "RequiredRank -> RankToText")
    t2s = call(ed, "/Script/Engine.KismetTextLibrary:Conv_TextToString", "TextToString"); connect(lib.find_output_pin(rt, "Result"), lib.find_input_pin(t2s, "InText"), "RankToText -> ToString")
    cc = call(ed, "/Script/Engine.KismetStringLibrary:Concat_StrStr", "Concat"); setval(cc, "A", "Door is locked - requires ")
    connect(lib.find_output_pin(t2s, "ReturnValue"), lib.find_input_pin(cc, "B"), "rank string -> Concat.B")
    s2t = call(ed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", "StringToText"); connect(lib.find_output_pin(cc, "ReturnValue"), lib.find_input_pin(s2t, "InString"), "Concat -> ToText")
    note = call(ed, "/Script/ConanSandbox.ConanPlayerController:ClientHUDShowNotification", "ClientHUDShowNotification")
    connect(as_pin(cast), lib.find_self_pin(note) or lib.find_input_pin(note, "self"), "AsConanPlayerController -> notify.self")
    connect(lib.find_output_pin(s2t, "ReturnValue"), lib.find_input_pin(note, "text"), "text -> notify")
    setval(note, "positive", "false")
    connect(then_out(cast), exec_in(note), "Cast.then -> notify")
compile_ok(door, [(ed, "EventGraph")], "BP_PL_Door")
for n in ed.list_all_nodes():
    if title(n) in ("Cast To ConanPlayerController", "ClientHUDShowNotification", "RankToText") or (n is gate):
        print(f"   NODE {title(n)!r}:", [(str(PL.get_pin_name(p)), [f'{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}' for c in PL.list_connected_pins(p)]) for p in lib.list_all_pins(n) if list(PL.list_connected_pins(p))])
if MODE == "real" and not failures: save(door, DOOR_DISK, "BP_PL_Door")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
