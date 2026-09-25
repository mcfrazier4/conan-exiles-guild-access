"""READ-ONLY: how to feed SetTextStyle's by-ref TSubclassOf pin: LoadClassAsset pins, class casts offered, class-typed variables."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
ld = call(ed, "/Script/Engine.KismetSystemLibrary:LoadClassAsset_Blocking", "LoadClass"); print("   LoadClassAsset pins:", pins(ld))
ss = call(ed, "/Script/ConanSandbox.GeneralText:SetTextStyle", "SetTextStyle"); print("   SetTextStyle pins:", pins(ss))
for n, nm in ((ld, "ReturnValue"), (ss, "NewStyle")):
    for p in lib.list_all_pins(n):
        if str(PL.get_pin_name(p)) == nm:
            t = PL.get_pin_type(p); print(f"   {nm}: {t}"); print("      ", {k: str(getattr(t, k, '?'))[:60] for k in ("pin_category", "pin_sub_category", "pin_sub_category_object", "is_reference")})
rv = lib.find_output_pin(ld, "ReturnValue"); print("   ReturnValue pin found:", rv is not None)
print("   actions on class pin (cast/conv):", [a for a in available(ed, [rv]) if re.search(r"Cast|Conv|Class", a)][:15])
print("   lib type helpers:", [d for d in dir(lib) if re.search(r"type|default", d.lower())])
ed.remove_nodes([ld, ss])
sec("done (read-only, not saved)")
