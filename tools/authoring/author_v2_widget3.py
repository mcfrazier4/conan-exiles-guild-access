"""v2 - Clan Ranks panel, third version: replaces the clan roster in place (Host = the open W_GuildView).
Run WITH -ModDevKit. GA_MODE=dry|real. Rebuilds the EventGraph from scratch every run.

Construct:
  header  : per rank an EditableTextBox (GM) and a GeneralText styled FS_Text_TableHeading (everyone else); visibility picks one
  rows    : GeneralText label (FS_Text_Body_3) + 4 WBP_ButtonCheckbox (toggled from the cache; enabled for GM except the GM column)
  buttons : WBP_ButtonBase 'Save' and 'Cancel' in the grid's last row
  every vanilla button is registered with Host.SetupNewChild so the window's input routing reaches it
Save   : names -> Server_ServerSetRankName_0 x4; table -> Server_ServerSetTable_0; restore roster; RemoveFromParent
Cancel : restore roster; RemoveFromParent
restore roster: if Host valid -> Host.GuildMembersList + ButtonShowOfflineMembers visible again
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
W_PATH = f"{LOCAL}/W_GA_ClanRanks"
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"; PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
CHK_C = "/Game/UI/Widgets/Buttons/WBP_ButtonCheckbox.WBP_ButtonCheckbox_C"; BTN_C = "/Game/UI/Widgets/Buttons/WBP_ButtonBase.WBP_ButtonBase_C"
SHOWN_PERMS = [0, 5]
GT = "/Script/ConanSandbox.GeneralText"; ST_HEAD = "/Game/UI/Styling/Texts/FS_Text_TableHeading.FS_Text_TableHeading_C"; ST_BODY = "/Game/UI/Styling/Texts/FS_Text_Body_3.FS_Text_Body_3_C"
M = "/Script/Engine.KismetMathLibrary:"; T = "/Script/Engine.KismetTextLibrary:"
FORLOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"
byte_t, bool_t, int_t = [lib.get_basic_type_by_name(x) for x in ("byte", "bool", "int")]
sec(f"mode = {MODE}")
wait_registry()
w = unreal.load_asset(W_PATH); check(w is not None, "loaded W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin(n, name): return pin_exact_in(n, name)
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def create_widget(cls_path, owner_pin, label):
    n = create_by_search(ed, [], ("CreateWidget",), f"CreateWidget {label}", exact="UserInterface|CreateWidget")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); connect(owner_pin, pin(n, "OwningPlayer"), f"{label}: owner"); return n
def construct(cls_path, label):
    n = create_by_search(ed, [], ("ConstructObjectfromClass",), f"Construct {label}", exact="Game|ConstructObjectfromClass")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); return n
def styled_text(style_cls, label, tail):
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
def add_to_grid(widget_pin, row, col, tail):
    a = call(ed, "/Script/UMG.UniformGridPanel:AddChildToUniformGrid", "AddChildToUniformGrid")
    connect(out(grid), selfpin(a), "PermGrid -> Add"); connect(widget_pin, pin(a, "Content"), "widget -> Add"); setval(a, "InRow", str(row)); setval(a, "InColumn", str(col))
    connect(tail, exec_in(a), "-> AddChildToUniformGrid"); return then_out(a)
def array_get(arr_pin, idx):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), "array -> Get")
    ip = pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index")
    if isinstance(idx, int): PL.set_pin_value(ip, str(idx))
    else: connect(idx, ip, "index -> Get")
    return out(g)
def array_add(arr_pin, item_pin=None, literal=None):
    a = create_by_search(ed, [arr_pin], ("Array", "Add"), "Array Add", exact="Utilities|Array|Add")
    connect(arr_pin, pin_exact_in(a, "TargetArray"), "array -> Add")
    if item_pin is not None: connect(item_pin, pin_exact_in(a, "NewItem"), "item -> Add")
    else: PL.set_pin_value(pin_exact_in(a, "NewItem"), literal)
    return a
def assign(obj_pin, exact, label):
    before = snapshot(ed)
    asg = create_by_search(ed, [obj_pin], tuple(exact.split("|")[-1:]), label, exact=exact)
    h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, f"{label}: handler"); h = h[0] if h else None
    sp = selfpin(asg)
    if sp is not None and not list(PL.list_connected_pins(sp)): connect(obj_pin, sp, f"{label}: self")
    return asg, h

# ---- rebuild: drop everything except the event nodes
keep = {n.get_name() for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_Event"}
ed.remove_nodes([n for n in ed.list_all_nodes() if n.get_name() not in keep]); print("   graph cleared (events kept)")
for nm in ("Cells", "CellIdx", "Boxes", "Comp", "Host"):   # recreate: types changed since the first version of the panel
    if nm in [str(v) for v in lib.list_member_variable_names(w)]: print(f"   removing old var {nm} ->", ed.remove_member_variable(nm))
lib.compile_blueprint(w)
for nm, t in (("Cells", lib.get_array_type(lib.get_object_reference_type(unreal.FLXButtonBase))), ("CellIdx", lib.get_array_type(int_t)), ("Boxes", lib.get_array_type(lib.get_object_reference_type(unreal.EditableTextBox))), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C))), ("Host", lib.get_object_reference_type(unreal.GuildViewBase))):
    check(lib.add_member_variable(w, nm, t), f"var {nm}")
lib.compile_blueprint(w)
grid = ed.add_get_member_variable_node("PermGrid"); check(grid is not None, "Get PermGrid")
title_n = ed.add_get_member_variable_node("TitleText"); close_n = ed.add_get_member_variable_node("CloseButton")
ev = [n for n in ed.list_all_nodes() if title(n) == "Event Construct"][0]; tail = then_out(ev)
gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"]); pc = out(gop, "ReturnValue")
gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(pc, pin(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
sc = ed.add_set_member_variable_node("Comp"); connect(out(gcb, "ReturnValue"), pin(sc, "Comp"), "-> Comp"); connect(tail, exec_in(sc), "-> Set Comp"); tail = then_out(sc)
comp = ed.add_get_member_variable_node("Comp")
names = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp), selfpin(names), "comp -> CachedNames")
allowed = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp), selfpin(allowed), "comp -> CachedAllowed")
myrank = ed.add_get_member_variable_node("CachedMyRank", PL_C); connect(out(comp), selfpin(myrank), "comp -> CachedMyRank")
is_gm = call(ed, M + "EqualEqual_ByteByte", "MyRank==3"); connect(out(myrank), pin(is_gm, "A"), "rank"); setval(is_gm, "B", "3")
tail = set_vis(out(title_n), "Collapsed", tail, "TitleText")
hide = call(ed, "/Script/UMG.Widget:SetVisibility", "hide CloseButton"); connect(out(close_n), selfpin(hide), "CloseButton"); setval(hide, "InVisibility", "Collapsed"); connect(tail, exec_in(hide), "-> hide"); tail = then_out(hide)
boxes = ed.add_get_member_variable_node("Boxes"); cells = ed.add_get_member_variable_node("Cells"); cellidx = ed.add_get_member_variable_node("CellIdx")
# header
for r in range(4):
    box = construct("/Script/UMG.EditableTextBox", f"name box {r}"); connect(tail, exec_in(box), "-> box"); tail = then_out(box); bp_ = out(box, "ReturnValue")
    stx = call(ed, "/Script/UMG.EditableTextBox:SetText", f"SetText(box {r})"); connect(bp_, selfpin(stx), "box")
    s2t = call(ed, T + "Conv_StringToText", "StringToText"); connect(array_get(out(names), r), pin(s2t, "InString"), f"name[{r}]"); connect(out(s2t, "ReturnValue"), pin(stx, "InText"), "text")
    connect(tail, exec_in(stx), "-> SetText"); tail = then_out(stx)
    tail = add_to_grid(bp_, 0, r + 1, tail)
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
    connect(t1, exec_in(jn), "GM -> join"); connect(t2, exec_in(jn), "other -> join"); tail = then_out(jn)
# rows
for row, perm in enumerate(SHOWN_PERMS, start=1):
    lp_, tail = styled_text(ST_BODY, f"label {perm}", tail)
    ptt = call(ed, f"{BPL_C}:PermToText", "PermToText"); setval(ptt, "Perm", str(perm))
    stl = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(label {perm})"); connect(lp_, selfpin(stl), "label"); connect(out(ptt, "Result"), pin(stl, "InText"), "text"); connect(tail, exec_in(stl), "-> SetText"); tail = then_out(stl)
    tail = add_to_grid(lp_, row, 0, tail)
    for rank in range(4):
        cw = create_widget(CHK_C, pc, f"cell {perm}/{rank}"); connect(tail, exec_in(cw), "-> CreateWidget"); tail = then_out(cw); cp = out(cw, "ReturnValue")
        tog = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetIsToggledOn", "SetIsToggledOn"); connect(cp, selfpin(tog), "cell"); connect(array_get(out(allowed), perm * 4 + rank), pin(tog, "NewIsToggledOn"), "allowed[i]"); setval(tog, "ShouldSendEvent", "false"); setval(tog, "IsInstantTransition", "true")
        connect(tail, exec_in(tog), "-> SetIsToggledOn"); tail = then_out(tog)
        en = call(ed, "/Script/UMG.Widget:SetIsEnabled", "enable cell"); connect(cp, selfpin(en), "cell")
        if rank == 3: setval(en, "bInIsEnabled", "false")
        else: connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?")
        connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
        tail = add_to_grid(cp, row, rank + 1, tail); tail = setup_child(cp, tail, f"cell {perm}/{rank}")
        a1 = array_add(out(cells), cp); connect(tail, exec_in(a1), "-> Cells.Add"); tail = then_out(a1)
        a2 = array_add(out(cellidx), literal=str(perm * 4 + rank)); connect(tail, exec_in(a2), "-> CellIdx.Add"); tail = then_out(a2)
# Save / Cancel
last_row = len(SHOWN_PERMS) + 1
sv = create_widget(BTN_C, pc, "Save"); connect(tail, exec_in(sv), "-> CreateWidget Save"); tail = then_out(sv)
sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", "SetLabel(Save)"); connect(out(sv, "ReturnValue"), selfpin(sl), "btn")
lt = call(ed, T + "Conv_StringToText", "Save text"); setval(lt, "InString", "Save"); connect(out(lt, "ReturnValue"), pin(sl, "NewLabel"), "text -> label"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
tail = add_to_grid(out(sv, "ReturnValue"), last_row, 1, tail); tail = setup_child(out(sv, "ReturnValue"), tail, "Save")
cv = create_widget(BTN_C, pc, "Cancel"); connect(tail, exec_in(cv), "-> CreateWidget Cancel"); tail = then_out(cv)
cl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", "SetLabel(Cancel)"); connect(out(cv, "ReturnValue"), selfpin(cl), "btn")
lt2 = call(ed, T + "Conv_StringToText", "Cancel text"); setval(lt2, "InString", "Cancel"); connect(out(lt2, "ReturnValue"), pin(cl, "NewLabel"), "text -> label"); connect(tail, exec_in(cl), "-> label"); tail = then_out(cl)
tail = add_to_grid(out(cv, "ReturnValue"), last_row, 2, tail); tail = setup_child(out(cv, "ReturnValue"), tail, "Cancel")
asg_s, h_save = assign(out(sv, "ReturnValue"), "Events|AssignSignalClicked", "Assign Save"); connect(tail, exec_in(asg_s), "-> Assign Save"); tail = then_out(asg_s)
lib.compile_blueprint(w)
asg_c, h_cancel = assign(out(cv, "ReturnValue"), "Events|AssignSignalClicked", "Assign Cancel"); connect(tail, exec_in(asg_c), "-> Assign Cancel"); tail = then_out(asg_c)
# Save handler: names, table, close
comp2 = ed.add_get_member_variable_node("Comp"); t = then_out(h_save)
boxes2 = ed.add_get_member_variable_node("Boxes")
for r in range(4):
    gt = call(ed, "/Script/UMG.EditableTextBox:GetText", f"GetText(box {r})"); connect(array_get(out(boxes2), r), selfpin(gt), "box")
    t2s = call(ed, T + "Conv_TextToString", "TextToString"); connect(out(gt, "ReturnValue"), pin(t2s, "InText"), "text")
    rpc = call(ed, f"{PL_C}:Server_ServerSetRankName_0", f"ServerSetRankName {r}"); connect(out(comp2), selfpin(rpc), "comp"); setval(rpc, "Rank", str(r)); connect(out(t2s, "ReturnValue"), pin(rpc, "Name"), "name")
    connect(t, exec_in(rpc), f"-> set name {r}"); t = then_out(rpc)
lp = ed.add_macro_node(FORLOOP); check(lp is not None, "ForLoop"); n_cells = len(SHOWN_PERMS) * 4
PL.set_pin_value(pin_exact_in(lp, "FirstIndex"), "0"); PL.set_pin_value(pin_exact_in(lp, "LastIndex"), str(n_cells - 1)); connect(t, pin_exact_in(lp, "execute"), "-> ForLoop"); idx = pin_exact_out(lp, "Index")
allowed2 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed2), "comp")
cells2 = ed.add_get_member_variable_node("Cells"); cellidx2 = ed.add_get_member_variable_node("CellIdx")
isc = call(ed, "/Script/ConanSandbox.FLXButtonBase:GetIsToggledOn", "GetIsToggledOn"); connect(array_get(out(cells2), idx), selfpin(isc), "cell[i]")
setel = create_by_search(ed, [out(allowed2)], ("Array", "SetArrayElem"), "Array Set", exact="Utilities|Array|SetArrayElem")
connect(out(allowed2), pin_exact_in(setel, "TargetArray"), "CachedAllowed -> Set"); connect(array_get(out(cellidx2), idx), pin_exact_in(setel, "Index"), "idx"); connect(out(isc, "ReturnValue"), pin_exact_in(setel, "Item"), "toggled")
connect(pin_exact_out(lp, "LoopBody"), exec_in(setel), "body -> Set")
rpc = call(ed, f"{PL_C}:Server_ServerSetTable_0", "ServerSetTable"); connect(out(comp2), selfpin(rpc), "comp"); allowed3 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed3), "comp"); connect(out(allowed3), pin(rpc, "Allowed"), "table")
connect(pin_exact_out(lp, "Completed"), exec_in(rpc), "Completed -> ServerSetTable")
def restore_and_close(tail, label):
    h = ed.add_get_member_variable_node("Host"); iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", f"IsValid(Host) {label}"); connect(out(h), pin(iv, "Object"), "Host")
    br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(tail, exec_in(br), f"{label} -> Branch")
    gl = ed.add_get_member_variable_node("GuildMembersList", "/Script/ConanSandbox.GuildViewBase"); connect(out(h), selfpin(gl), "Host -> roster")
    gb = ed.add_get_member_variable_node("ButtonShowOfflineMembers", "/Script/ConanSandbox.GuildViewBase"); connect(out(h), selfpin(gb), "Host -> show offline")
    t = set_vis(out(gl), "Visible", then_out(br), f"roster ({label})"); t = set_vis(out(gb), "Visible", t, f"show offline ({label})")
    rf = call(ed, "/Script/UMG.Widget:RemoveFromParent", f"RemoveFromParent ({label})"); connect(t, exec_in(rf), "-> remove"); connect(lib.find_else_pin(br), exec_in(rf), "no host -> remove")
restore_and_close(then_out(rpc), "save")
restore_and_close(then_out(h_cancel), "cancel")
sec("compile")
compile_ok(w, [(ed, "EventGraph")], "W_GA_ClanRanks")
if MODE == "real" and not failures: save(w, os.path.join(DISK_LOCAL, "W_GA_ClanRanks.uasset"), "W_GA_ClanRanks")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
