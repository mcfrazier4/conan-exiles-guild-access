"""READ-ONLY: editable-text subclasses, and whether the nodes the replacement panel needs are offered on W_GA_ClanRanks."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
sec("EditableText subclasses / style consumers")
for base_name in ("EditableTextBox", "EditableText", "MultiLineEditableTextBox"):
    b = getattr(unreal, base_name); bs = set(dir(b))
    for cname in [c for c in dir(unreal) if c != base_name and isinstance(getattr(unreal, c, None), type) and issubclass(getattr(unreal, c), b)]:
        print(f"   {cname} <- {base_name}: {[d for d in dir(getattr(unreal, cname)) if not d.startswith('_') and d not in bs][:12]}")
sec("style asset classes: parent class")
for p in ("/Game/UI/Styling/Texts/FS_Text_TableHeading", "/Game/UI/Styling/Texts/FS_Text_Body_3", "/Game/UI/Styling/Texts/EditableTexts/FS_EditableText_Clear", "/Game/UI/Styling/Buttons/FS_Button_Checkbox_Clan"):
    a = unreal.load_asset(p); print(f"   {p.split('/')[-1]}: parent {lib.get_blueprint_parent_class(a).get_name() if a else 'MISSING'}")
sec("nodes offered on W_GA_ClanRanks")
w = unreal.load_asset(f"{LOCAL}/W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
lib.add_member_variable(w, "ZZ_Host", lib.get_object_reference_type(unreal.GuildViewBase)); lib.add_member_variable(w, "ZZ_Txt", lib.get_object_reference_type(unreal.GeneralText)); lib.compile_blueprint(w)
gh = ed.add_get_member_variable_node("ZZ_Host"); gt = ed.add_get_member_variable_node("ZZ_Txt")
hp = lib.list_output_pins(gh)[0]; tp = lib.list_output_pins(gt)[0]
print("   on GuildViewBase pin:", [a for a in available(ed, [hp]) if re.search(r"SetupNewChild|Setup New Child|GuildMembersList|Guild Members List|ShowOffline|Show Offline|SetWindow|Set Window", a)][:12])
print("   on GeneralText pin:", [a for a in available(ed, [tp]) if re.search(r"TextStyle|Text Style|SetText|Set Text|Justif", a)][:12])
print("   ConstructObject:", [a for a in available(ed, []) if re.search(r"Construct Object|ConstructObject", a)][:5])
gm = call(ed, "/Script/ConanSandbox.GuildViewBase:GetGuildMembersList", "GetGuildMembersList?") if False else None
# C++ read-only props: is there a getter function or only a variable-get?
for fn in ("GuildMembersList", "ButtonShowOfflineMembers"):
    try: g = ed.add_get_member_variable_node(fn, "/Script/ConanSandbox.GuildViewBase"); print(f"   Get {fn}: {g is not None} pins {pins(g) if g else ''}"); ed.remove_nodes([g]) if g else None
    except Exception as e: print(f"   Get {fn}: ERR {str(e)[:80]}")
lp = None
ed.remove_nodes([gh, gt]); ed.remove_member_variable("ZZ_Host"); ed.remove_member_variable("ZZ_Txt")
sec("done (read-only; temp vars removed, not saved)")
