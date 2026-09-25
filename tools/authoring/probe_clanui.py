"""READ-ONLY: how the clan screen's button bar, buttons, checkboxes and text styles work."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
def dump_node(n):
    print(f"   NODE [{n.get_class().get_name()}] {title(n)!r}")
    for p in lib.list_all_pins(n):
        d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
        v = PL.get_pin_value(p); conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
        if v or conns: print(f"      {d} {str(PL.get_pin_name(p)):24} val={v[:70]!r} -> {conns}")
for path in ("/Game/UI/Widgets/General/WBP_ButtonBar", "/Game/UI/Widgets/Buttons/WBP_ButtonBase", "/Game/UI/Widgets/Buttons/WBP_ButtonCheckbox", "/Game/UI/Widgets/Guild/W_GuildView"):
    bp = unreal.load_asset(path); sec(path)
    if not bp: print("   MISSING"); continue
    print("   parent:", lib.get_blueprint_parent_class(bp))
    print("   dispatchers:", [str(d) for d in lib.list_event_dispatchers(bp)])
    print("   graphs:", [str(g) for g in lib.list_graph_names(bp)])
    print("   own variables:", [str(v) for v in lib.list_member_variable_names(bp) if not str(v).startswith("/Script/")][:30])
    ed = GE.get_graph_editor_by_name(bp, "EventGraph")
    if ed:
        for n in ed.list_all_nodes():
            t = title(n)
            if re.search(r"ButtonBar|Button|Clicked|Index|Switch|Leave|Close", t) and n.get_class().get_name() not in ("K2Node_Knot",): dump_node(n)
sec("C++: GuildViewBase / ButtonBar-related classes")
base = set(dir(unreal.Object))
for cname in [c for c in dir(unreal) if re.search(r"ButtonBar|ButtonBase|TextStyle|ButtonStyle|StyleAsset|ConanText|ConanButton|CheckboxButton", c)]:
    c = getattr(unreal, cname); print(f"   {cname}:", [d for d in dir(c) if not d.startswith("_") and d not in base][:25])
print("   GuildViewBase:", [d for d in dir(unreal.GuildViewBase) if not d.startswith("_") and d not in base])
sec("done (read-only)")
