"""READ-ONLY: (1) the server-side denial sites: what feeds each EventGraph RankToText and which nearby pins are ConanCharacter;
(2) can a roster row reach its rank badge (Image brush readable from BP)?; (3) Delay node; (4) W_Guild_NamePopup child feasibility."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def src(p):
    return [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
sec("EventGraph RankToText sites")
for p in ("/Game/Systems/Building/Placeables/BP_PlaceableItemContainer", "/Game/Systems/Building/Placeables/BP_PL_Door", "/Game/Systems/Building/BP_BuildDoor"):
    bp = unreal.load_asset(p); ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    for n in [n for n in ed.list_all_nodes() if title(n) == "RankToText"]:
        rank_src = src(lib.find_input_pin(n, "Rank")); cons = [PL.get_owning_node(c) for q in lib.list_output_pins(n) for c in PL.list_connected_pins(q)]
        # walk consumers to the exec node that shows the message
        chain = []; cur = cons[0] if cons else None; hops = 0
        while cur is not None and hops < 6:
            chain.append(title(cur)); nxt = [PL.get_owning_node(c) for q in lib.list_output_pins(cur) for c in PL.list_connected_pins(q)]; cur = nxt[0] if nxt else None; hops += 1
        print(f"   {p.split('/')[-1]}: Rank <- {rank_src}; chain -> {chain}")
        # the exec node at the end: what feeds its self/target and which of ITS inputs come from a character
        if cur is None and chain:
            pass
    # nodes with a ConanCharacter output pin near HUD notification
    for n in ed.list_all_nodes():
        if title(n) in ("ClientHUDShowNotification", "Cast To ConanPlayerController"):
            print(f"      {title(n)}: {[(str(PL.get_pin_name(q)), src(q)) for q in lib.list_input_pins(n)]}")
sec("Image pin: brush actions (roster rank badge)")
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
lib.add_member_variable(w, "ZZ_Img", lib.get_object_reference_type(unreal.Image)); lib.compile_blueprint(w)
g = ed.add_get_member_variable_node("ZZ_Img"); ip = lib.list_output_pins(g)[0]
print("   image actions:", [a for a in available(ed, [ip]) if re.search(r"Brush|Texture|DesiredSize|ColorAndOpacity", a)][:14])
print("   delay/timer:", [a for a in available(ed, []) if re.search(r"\|Delay$|\|Delay\b|SetTimer", a)][:6])
ed.remove_nodes([g]); ed.remove_member_variable("ZZ_Img")
sec("W_ListEntry: variables usable from an override")
le = unreal.load_asset("/Game/UI/Widgets/Guild/W_ListEntry"); print("   member vars:", [str(v) for v in lib.list_member_variable_names(le) if not str(v).startswith("/Script/")])
sec("W_Guild_NamePopup: inherited widget vars for a child class")
np_ = unreal.load_asset("/Game/UI/Widgets/Guild/W_Guild_NamePopup"); print("   member vars:", [str(v) for v in lib.list_member_variable_names(np_) if not str(v).startswith("/Script/")])
sec("done (read-only; temp var removed, not saved)")
