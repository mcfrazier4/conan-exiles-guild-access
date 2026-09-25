"""Remove the 'Clan Ranks' radial entries (owner decision: the panel lives in the Clan tab).
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
adds = [n for n in nodes_titled(ed, "AddItem") if "ClanRanks" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "")]
if not adds: print("   nothing to remove")
else:
    add = adds[0]
    # walk forward from the AddItem: Assign node, its custom event, and the handler chain; walk back: the member Branch, IsGuildMemberRank, and the Sequence we inserted
    victims = set(); frontier = [add]
    while frontier:
        n = frontier.pop();
        if n.get_name() in victims: continue
        victims.add(n.get_name())
        for p in lib.list_output_pins(n):
            for c in PL.list_connected_pins(p):
                m = PL.get_owning_node(c)
                if title(m) not in ("Sequence",) and m.get_class().get_name() != "K2Node_ExecutionSequence": frontier.append(m)
        for p in lib.list_input_pins(n):
            for c in PL.list_connected_pins(p):
                m = PL.get_owning_node(c)
                if title(m) in ("IsGuildMemberRank", "Branch", "GetPlayerController", "GetComponentByClass") and m.get_name() not in victims:
                    # only our member-branch feeder chain (fed from the Sequence's then_1), never the rank-menu branch
                    feeders = [title(PL.get_owning_node(cc)) for q in lib.list_input_pins(m) for cc in PL.list_connected_pins(q)]
                    if "Sequence" in feeders or title(m) in ("GetPlayerController", "GetComponentByClass"): frontier.append(m)
    # find the Assign node bound to this AddItem and its custom event
    for n in ed.list_all_nodes():
        if n.get_class().get_name() == "K2Node_AssignDelegate":
            srcs = [PL.get_owning_node(c) for p in lib.list_input_pins(n) for c in PL.list_connected_pins(p)]
            if any(s.get_name() == add.get_name() for s in srcs):
                victims.add(n.get_name())
                for p in lib.list_input_pins(n):
                    for c in PL.list_connected_pins(p):
                        m = PL.get_owning_node(c)
                        if m.get_class().get_name() == "K2Node_CustomEvent":
                            victims.add(m.get_name())
                            for q in lib.list_output_pins(m):
                                for cc in PL.list_connected_pins(q):
                                    mm = PL.get_owning_node(cc); victims.add(mm.get_name())
                                    for r in lib.list_input_pins(mm):
                                        for ccc in PL.list_connected_pins(r): victims.add(PL.get_owning_node(ccc).get_name())
    nodes = [n for n in ed.list_all_nodes() if n.get_name() in victims]
    print("   removing:", sorted(set(title(n) for n in nodes)))
    # the Sequence we inserted: re-link its then_0 target directly from its feeder, then drop it
    # the Sequence we inserted feeds (then_1) IsGuildMemberRank -> Branch -> AddItem: collect that side chain too
    seqs = []
    for n in ed.list_all_nodes():
        if n.get_class().get_name() != "K2Node_ExecutionSequence": continue
        chain = []; cur = pin_exact_out(n, "then_1"); hops = 0
        while cur is not None and hops < 8:
            nxt = [PL.get_owning_node(c) for c in PL.list_connected_pins(cur)]
            if not nxt: break
            m = nxt[0]; chain.append(m); hops += 1
            cur = then_out(m)
        if any(m.get_name() in victims for m in chain):
            seqs.append(n)
            for m in chain: victims.add(m.get_name())
    nodes = [n for n in ed.list_all_nodes() if n.get_name() in victims]
    for s in seqs:
        feeder = list(PL.list_connected_pins(exec_in(s))); t0 = list(PL.list_connected_pins(pin_exact_out(s, "then_0")))
        if feeder and t0: PL.break_pin_links(exec_in(s)); connect(feeder[0], t0[0], "feeder -> original branch (Sequence removed)")
        nodes.append(s)
    ed.remove_nodes(nodes)
    check(not any("ClanRanks" in (PL.get_pin_value(lib.find_input_pin(n, "label")) or "") for n in nodes_titled(ed, "AddItem")), "radial entry gone")
compile_ok(bp, [(ed, "EventGraph")], TARGET)
if MODE == "real" and not failures: save(bp, os.path.join(DISK_CONTENT, REL), TARGET)
elif MODE == "real": print("   NOT SAVING: failures above")
result()
