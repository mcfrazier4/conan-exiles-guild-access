"""After a rank is picked in the radial submenu, close the radial (the entry subtitle cannot be updated in place).
Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=container|door|builddoor. Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "container").lower()
CLASSES = {"container": ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", r"Systems\Building\Placeables\BP_PlaceableItemContainer.uasset"),
           "door": ("/Game/Systems/Building/Placeables/BP_PL_Door", r"Systems\Building\Placeables\BP_PL_Door.uasset"),
           "builddoor": ("/Game/Systems/Building/BP_BuildDoor", r"Systems\Building\BP_BuildDoor.uasset")}
PATH, REL = CLASSES[TARGET]
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
bp = unreal.load_asset(PATH); ed = GE.get_graph_editor_by_name(bp, "EventGraph")
done = 0
for rpc in [n for n in ed.list_all_nodes() if title(n) == "Server_ServerSetRequiredRank_0"]:
    if list(PL.list_connected_pins(then_out(rpc))): continue   # already followed by something (FadeOutMenu)
    ev = [PL.get_owning_node(c) for c in PL.list_connected_pins(exec_in(rpc))]
    if not ev or ev[0].get_class().get_name() != "K2Node_CustomEvent": continue
    entry = lib.find_output_pin(ev[0], "menuEntry")
    fo = call(ed, "/Script/ConanSandbox.RadialMenuEntry:FadeOutMenu", "FadeOutMenu")
    connect(entry, lib.find_self_pin(fo) or pin_exact_in(fo, "self"), "menuEntry -> FadeOutMenu"); connect(then_out(rpc), exec_in(fo), "rpc -> FadeOutMenu"); done += 1
print(f"   FadeOutMenu added after {done} rank clicks")
compile_ok(bp, [(ed, "EventGraph")], TARGET)
if MODE == "real" and not failures: save(bp, os.path.join(DISK_CONTENT, REL), TARGET)
elif MODE == "real": print("   NOT SAVING: failures above")
result()
