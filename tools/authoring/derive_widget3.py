"""One-off: derive author_v2_widget3.py from author_v2_widget2.py (kept so the derivation is reviewable)."""
import os
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "author_v2_widget2.py")).read()
def rep(a, b):
    global src
    assert a in src, a[:80]
    src = src.replace(a, b)
rep('''"""v2 - Clan Ranks panel, second version: vanilla-styled widgets, edits buffered until Save.
Run WITH -ModDevKit. GA_MODE=dry|real. Rebuilds the EventGraph from scratch every run.

Construct:
  header  : 4 EditableTextBox (rank names; enabled for the guild master)
  rows    : label + 4 WBP_ButtonCheckbox (toggled from the cache; enabled for GM except the GM column)
  buttons : WBP_ButtonBase 'Save' and 'Cancel' in the grid's last row
Save   : names -> Server_ServerSetRankName_0 x4; table from the checkboxes -> Server_ServerSetTable_0; RemoveFromParent
Cancel : RemoveFromParent
"""''', '''"""v2 - Clan Ranks panel, third version: replaces the clan roster in place (Host = the open W_GuildView).
Run WITH -ModDevKit. GA_MODE=dry|real. Rebuilds the EventGraph from scratch every run.

Construct:
  header  : per rank an EditableTextBox (GM) and a GeneralText styled FS_Text_TableHeading (everyone else); visibility picks one
  rows    : GeneralText label (FS_Text_Body_3) + 4 WBP_ButtonCheckbox (toggled from the cache; enabled for GM except the GM column)
  buttons : WBP_ButtonBase 'Save' and 'Cancel' in the grid's last row
  every vanilla button is registered with Host.SetupNewChild so the window's input routing reaches it
Save   : names -> Server_ServerSetRankName_0 x4; table -> Server_ServerSetTable_0; restore roster; RemoveFromParent
Cancel : restore roster; RemoveFromParent
restore roster: if Host valid -> Host.GuildMembersList + ButtonShowOfflineMembers visible again
"""''')
rep('SHOWN_PERMS = [0, 5]', 'SHOWN_PERMS = [0, 5]\nGT = "/Script/ConanSandbox.GeneralText"; ST_HEAD = "/Game/UI/Styling/Texts/FS_Text_TableHeading.FS_Text_TableHeading_C"; ST_BODY = "/Game/UI/Styling/Texts/FS_Text_Body_3.FS_Text_Body_3_C"')
rep('for nm in ("Cells", "CellIdx", "Boxes", "Comp"):', 'for nm in ("Cells", "CellIdx", "Boxes", "Comp", "Host"):')
rep('("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C)))):', '("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C))), ("Host", lib.get_object_reference_type(unreal.GuildViewBase))):')
rep('def add_to_grid(widget_pin, row, col, tail):', '''def styled_text(style_cls, label, tail):
    """ConstructObject(GeneralText) -> SetTextStyle(style). Returns (text pin, tail)."""
    n = construct(GT, label); connect(tail, exec_in(n), f"-> {label}"); tail = then_out(n); tp = out(n, "ReturnValue")
    ss = call(ed, "/Script/ConanSandbox.GeneralText:SetTextStyle", f"SetTextStyle({label})"); connect(tp, selfpin(ss), "text")
    sp = next((p for p in lib.list_input_pins(ss) if "Style" in str(PL.get_pin_name(p))), None); check(sp is not None, f"{label}: style pin")
    # by-ref class param: feed it from a blocking class load with a literal soft path
    ld = call(ed, "/Script/Engine.KismetSystemLibrary:LoadClassAsset_Blocking", f"LoadClass({label})"); lp = next((p for p in lib.list_input_pins(ld) if "Class" in str(PL.get_pin_name(p))), None)
    check(lp is not None and PL.set_pin_value(lp, style_cls), f"{label}: style class literal"); connect(tail, exec_in(ld), "-> LoadClass"); tail = then_out(ld)
    rv = out(ld, "ReturnValue")   # generic Class -> TSubclassOf<TextStyleDataAsset> needs a class cast
    cast = create_by_search(ed, [rv], ("Casting", "CastToTextStyleDataAssetClass"), f"class cast ({label})", exact="Utilities|Casting|CastToTextStyleDataAssetClass")
    connect(rv, pin_exact_in(cast, "Object") or next((p for p in lib.list_input_pins(cast) if str(PL.get_pin_name(p)) not in ("execute",)), None), "class -> cast")
    connect(tail, exec_in(cast), "-> cast"); tail = then_out(cast)
    connect(as_pin(cast), sp, "cast -> style"); connect(tail, exec_in(ss), "-> SetTextStyle"); return tp, then_out(ss)
def setup_child(widget_pin, tail, label):
    """Host.SetupNewChild(widget): registers a runtime-created vanilla button with the clan window's input routing."""
    h = ed.add_get_member_variable_node("Host"); s = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", f"SetupNewChild({label})")
    cp_ = next((p for p in lib.list_input_pins(s) if str(PL.get_pin_name(p)) not in ("self", "execute")), None); check(cp_ is not None, f"SetupNewChild({label}) child pin {pins(s)}")
    connect(out(h), selfpin(s), "Host"); connect(widget_pin, cp_, "child"); connect(tail, exec_in(s), "-> SetupNewChild"); return then_out(s)
def set_vis(widget_pin, vis, tail, label):
    v = call(ed, "/Script/UMG.Widget:SetVisibility", f"SetVisibility({label})"); connect(widget_pin, selfpin(v), label); setval(v, "InVisibility", vis); connect(tail, exec_in(v), f"-> {label} {vis}"); return then_out(v)
def add_to_grid(widget_pin, row, col, tail):''')
rep('''    en = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"enable box {r}"); connect(bp_, selfpin(en), "box"); connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?"); connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
    tail = add_to_grid(bp_, 0, r + 1, tail)
    a = array_add(out(boxes), bp_); connect(tail, exec_in(a), "-> Boxes.Add"); tail = then_out(a)''', '''    tail = add_to_grid(bp_, 0, r + 1, tail)
    a = array_add(out(boxes), bp_); connect(tail, exec_in(a), "-> Boxes.Add"); tail = then_out(a)
    hp, tail = styled_text(ST_HEAD, f"heading {r}", tail)
    sth = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(heading {r})"); connect(hp, selfpin(sth), "heading"); connect(out(s2t, "ReturnValue"), pin(sth, "InText"), "text"); connect(tail, exec_in(sth), "-> SetText"); tail = then_out(sth)
    jc = ed.add_set_member_variable_node("Justification", "/Script/UMG.TextBlock"); check(jc is not None, f"Set Justification {r}"); connect(hp, selfpin(jc), "heading"); PL.set_pin_value(pin_exact_in(jc, "Justification"), "Center"); connect(tail, exec_in(jc), "-> center"); tail = then_out(jc)
    tail = add_to_grid(hp, 0, r + 1, tail)
    # GM: box Visible, heading Collapsed; others: box Collapsed, heading Visible; both branches rejoin on one node
    br = ed.add_branch_node(); connect(out(is_gm, "ReturnValue"), lib.find_condition_pin(br), "GM?"); connect(tail, exec_in(br), "-> Branch GM")
    t1 = set_vis(bp_, "Visible", then_out(br), f"box {r}"); t1 = set_vis(hp, "Collapsed", t1, f"heading {r}")
    t2 = set_vis(bp_, "Collapsed", lib.find_else_pin(br), f"box {r}"); t2 = set_vis(hp, "Visible", t2, f"heading {r}")
    jn = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"enable box {r}"); connect(bp_, selfpin(jn), "box"); setval(jn, "bInIsEnabled", "true")
    connect(t1, exec_in(jn), "GM -> join"); connect(t2, exec_in(jn), "other -> join"); tail = then_out(jn)''')
rep('''    lab = construct("/Script/UMG.TextBlock", f"label {perm}"); connect(tail, exec_in(lab), "-> label"); tail = then_out(lab)
    ptt = call(ed, f"{BPL_C}:PermToText", "PermToText"); setval(ptt, "Perm", str(perm))
    stl = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(label {perm})"); connect(out(lab, "ReturnValue"), selfpin(stl), "label"); connect(out(ptt, "Result"), pin(stl, "InText"), "text"); connect(tail, exec_in(stl), "-> SetText"); tail = then_out(stl)
    tail = add_to_grid(out(lab, "ReturnValue"), row, 0, tail)''', '''    lp_, tail = styled_text(ST_BODY, f"label {perm}", tail)
    ptt = call(ed, f"{BPL_C}:PermToText", "PermToText"); setval(ptt, "Perm", str(perm))
    stl = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(label {perm})"); connect(lp_, selfpin(stl), "label"); connect(out(ptt, "Result"), pin(stl, "InText"), "text"); connect(tail, exec_in(stl), "-> SetText"); tail = then_out(stl)
    tail = add_to_grid(lp_, row, 0, tail)''')
rep('''        tail = add_to_grid(cp, row, rank + 1, tail)
        a1 = array_add(out(cells), cp)''', '''        tail = add_to_grid(cp, row, rank + 1, tail); tail = setup_child(cp, tail, f"cell {perm}/{rank}")
        a1 = array_add(out(cells), cp)''')
rep('tail = add_to_grid(out(sv, "ReturnValue"), last_row, 1, tail)', 'tail = add_to_grid(out(sv, "ReturnValue"), last_row, 1, tail); tail = setup_child(out(sv, "ReturnValue"), tail, "Save")')
rep('tail = add_to_grid(out(cv, "ReturnValue"), last_row, 2, tail)', 'tail = add_to_grid(out(cv, "ReturnValue"), last_row, 2, tail); tail = setup_child(out(cv, "ReturnValue"), tail, "Cancel")')
rep('''st = call(ed, "/Script/UMG.TextBlock:SetText", "SetText(title)"); connect(out(title_n), selfpin(st), "TitleText"); setval(st, "InText", text_lit("ClanRanksTitle", "Clan Ranks")); connect(tail, exec_in(st), "-> title"); tail = then_out(st)''',
    '''tail = set_vis(out(title_n), "Collapsed", tail, "TitleText")''')
rep('''rfp = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent"); connect(then_out(rpc), exec_in(rfp), "-> close")
rfp2 = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent (cancel)"); connect(then_out(h_cancel), exec_in(rfp2), "cancel -> close")''',
    '''def restore_and_close(tail, label):
    h = ed.add_get_member_variable_node("Host"); iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", f"IsValid(Host) {label}"); connect(out(h), pin(iv, "Object"), "Host")
    br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(tail, exec_in(br), f"{label} -> Branch")
    gl = ed.add_get_member_variable_node("GuildMembersList", "/Script/ConanSandbox.GuildViewBase"); connect(out(h), selfpin(gl), "Host -> roster")
    gb = ed.add_get_member_variable_node("ButtonShowOfflineMembers", "/Script/ConanSandbox.GuildViewBase"); connect(out(h), selfpin(gb), "Host -> show offline")
    t = set_vis(out(gl), "Visible", then_out(br), f"roster ({label})"); t = set_vis(out(gb), "Visible", t, f"show offline ({label})")
    rf = call(ed, "/Script/UMG.Widget:RemoveFromParent", f"RemoveFromParent ({label})"); connect(t, exec_in(rf), "-> remove"); connect(lib.find_else_pin(br), exec_in(rf), "no host -> remove")
restore_and_close(then_out(rpc), "save")
restore_and_close(then_out(h_cancel), "cancel")''')
open(os.path.join(here, "author_v2_widget3.py"), "w").write(src); print("written author_v2_widget3.py", len(src))
